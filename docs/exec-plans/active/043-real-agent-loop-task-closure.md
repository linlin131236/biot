# M43 Real Agent Loop Task Closure Integration

## 目标
把 M42 的任务闭环记录层接入真实 Goal / Run / Agent Loop 链路。闭环记录 run、goal、loop 状态、工具结果、权限等待、失败和完成摘要。

## 范围
- TaskClosureService 负责绑定 run / goal，并按 run / goal 查询闭环。
- Harness 在 Agent Loop 结束后把结果同步到绑定闭环。
- 桌面端闭环面板支持创建、绑定当前运行、绑定当前目标、刷新状态。
- 共享协议和客户端 API 暴露绑定与查询接口。

## 不做
- 不执行工具。
- 不批准 permission。
- 不 push / release / delete。
- 不绕过 PermissionGate。
- 不新增 M44 能力。

## 验证
- 后端集成：create run -> create closure -> bind run -> run loop -> get by run。
- pending permission 映射为 waiting_permission，并保留权限队列。
- max_steps 映射为 stopped。
- 无绑定 closure 时 run_agent_loop 保持旧行为。
- 桌面 App 狗粮覆盖创建闭环、绑定当前运行、刷新中文状态。
