"""Test Runner Integration API. Safe test execution with budget control."""
from fastapi import APIRouter, HTTPException

from bolt_core.test_runner_integration import TestRunnerIntegration


def create_test_runner_integration_router(runner: TestRunnerIntegration | None = None) -> APIRouter:
    """创建测试运行集成 API 路由。"""
    if runner is None:
        runner = TestRunnerIntegration()

    router = APIRouter(tags=["tools"])

    @router.get("/tools/test-runner/available")
    def list_available_tests() -> dict:
        """列出所有白名单测试命令。只读。"""
        return runner.list_available()

    @router.post("/tools/test-runner/run")
    def run_test(payload: dict) -> dict:
        """运行白名单测试命令。不自动修复失败。

        请求体: { "test_id": "backend_unit", "extra_args": ["tests/test_tool_registry.py"] }
        """
        test_id = str(payload.get("test_id", "")).strip()
        if not test_id:
            raise HTTPException(status_code=400, detail="test_id 不能为空")

        extra_args = payload.get("extra_args", [])
        if not isinstance(extra_args, list):
            extra_args = []

        result = runner.run(test_id, extra_args)
        return {
            "result": result.to_dict(),
            "disclaimer": "测试运行器仅执行白名单命令，不自动修复失败。失败需人工诊断。",
        }

    @router.get("/tools/test-runner/history")
    def get_history() -> dict:
        """查看测试运行历史。只读。"""
        return {
            "history": runner.history(),
            "total": len(runner.history()),
        }

    return router
