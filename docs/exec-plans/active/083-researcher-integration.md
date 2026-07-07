# M83 Exec Plan — Researcher Integration

## 目标
接入 Researcher 只读资料角色。Researcher 只能读指定资料/代码，输出摘要和 source_refs，不能实现、不能改文件。

## 参考资料
- Phase16 Lesson 08 Role Specialization（角色边界：只读、不越界）
- Flock架构分析（Planner 只读 + source_refs 强制）
- bolt-knowledge-source-index.md（2-4 篇规则）

## 产出
- `researcher_integration.py`
- `researcher_integration_api.py`
- tests
- app.py 注册
