"""Multi-Agent Workflow API router. Manages Planner → Builder → Reviewer
pipeline workflows with strict transition validation."""
from fastapi import APIRouter, HTTPException

from bolt_core.multi_agent_workflow import MultiAgentWorkflowService


def create_multi_agent_workflow_router() -> APIRouter:
    router = APIRouter(tags=["multi-agent-workflow"])
    service = MultiAgentWorkflowService()

    @router.post("/workflows")
    def create_workflow(payload: dict) -> dict:
        """创建新的多 Agent 工作流。初始状态为"规划中"。

        payload: { title_cn: str }
        示例：POST /workflows
        Body: {"title_cn":"实现用户登录功能"}
        """
        title_cn = payload.get("title_cn", "")
        if not title_cn:
            raise HTTPException(status_code=400, detail="缺少 title_cn 字段。")
        wf = service.create_workflow(title_cn)
        return wf.to_dict()

    @router.get("/workflows")
    def list_workflows() -> list[dict]:
        """列出所有工作流。只读。

        示例：GET /workflows
        """
        return [wf.to_dict() for wf in service.list_workflows()]

    @router.get("/workflows/{workflow_id}")
    def get_workflow(workflow_id: str) -> dict:
        """获取单个工作流详情。只读。

        示例：GET /workflows/wf-abc123
        """
        wf = service.get_workflow(workflow_id)
        if wf is None:
            raise HTTPException(
                status_code=404,
                detail=f"未找到工作流：{workflow_id}。",
            )
        return wf.to_dict()

    @router.get("/workflows/{workflow_id}/status-summary")
    def status_summary(workflow_id: str) -> dict:
        """获取工作流中文状态摘要。只读。

        示例：GET /workflows/wf-abc123/status-summary
        """
        result = service.status_summary_cn(workflow_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    @router.post("/workflows/{workflow_id}/planner-output")
    def assign_planner_output(workflow_id: str, payload: dict) -> dict:
        """提交规划者输出。将状态从"规划中"转移到"待构建"。

        payload: { task_breakdown, risk_assessment, assignment, source_refs, context? }
        """
        result = service.assign_planner_output(
            workflow_id=workflow_id,
            task_breakdown=payload.get("task_breakdown", []),
            risk_assessment=payload.get("risk_assessment", "medium"),
            assignment=payload.get("assignment", {}),
            source_refs=payload.get("source_refs", []),
            context=payload.get("context", ""),
        )
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.post("/workflows/{workflow_id}/builder-output")
    def assign_builder_output(workflow_id: str, payload: dict) -> dict:
        """提交构建者输出。将状态从"构建中"/"需修改"转移到"待审查"。

        payload: { code_changes, tests, evidence_refs, source_refs, context? }

        构建者不能自我批准——如果 context 与审查者相同，将被阻断。
        """
        result = service.assign_builder_output(
            workflow_id=workflow_id,
            code_changes=payload.get("code_changes", ""),
            tests=payload.get("tests", ""),
            evidence_refs=payload.get("evidence_refs", []),
            source_refs=payload.get("source_refs", []),
            context=payload.get("context", ""),
        )
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.post("/workflows/{workflow_id}/reviewer-output")
    def assign_reviewer_output(workflow_id: str, payload: dict) -> dict:
        """提交审查者输出。根据结论转移状态。

        required verdict: approved / changes_requested / blocked

        硬阻断：
        - 审查者与构建者同上下文（自我批准）
        - 存在 P1/P2 问题却 approved
        - 缺 evidence/source_refs

        示例：POST /workflows/wf-abc/reviewer-output
        Body: {"findings":[], "evidence":["code:10"], "tests_status":"passed",
               "residual_risks":[], "verdict":"approved", "source_refs":["..."],
               "context":"ctx-reviewer-1"}
        """
        result = service.assign_reviewer_output(
            workflow_id=workflow_id,
            findings=payload.get("findings", []),
            evidence=payload.get("evidence", []),
            tests_status=payload.get("tests_status", ""),
            residual_risks=payload.get("residual_risks", []),
            verdict=payload.get("verdict", ""),
            source_refs=payload.get("source_refs", []),
            context=payload.get("context", ""),
        )
        if not result.valid:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    @router.post("/workflows/{workflow_id}/validate-transition")
    def validate_transition(workflow_id: str, payload: dict) -> dict:
        """诊断性检查：某状态转移是否合法？不改变实际状态。

        payload: { target_state: str }
        示例：POST /workflows/wf-abc/validate-transition
        Body: {"target_state":"approved"}
        """
        target_state = payload.get("target_state", "")
        if not target_state:
            raise HTTPException(status_code=400, detail="缺少 target_state 字段。")
        result = service.validate_transition(workflow_id, target_state)
        if result.blocked:
            raise HTTPException(status_code=400, detail=result.message_cn)
        return result.to_dict()

    return router
