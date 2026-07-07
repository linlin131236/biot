# M56 Decision: Execution Evidence Redaction

## 决策
新增单一模块 `evidence_redactor.py`，提供一个 `redact(text: str) -> str` 函数。在写入 audit store / closure / timeline 的字符串路径上调用此函数。保守模式：只替换明确匹配的模式，不信任复杂正则。

## 脱敏模式
- `OPENAI_API_KEY=...` → `OPENAI_API_KEY=[已脱敏]`
- `API_KEY=...` → `API_KEY=[已脱敏]`
- `TOKEN=...` → `TOKEN=[已脱敏]`
- `SECRET=...` → `SECRET=[已脱敏]`
- `PASSWORD=...` → `PASSWORD=[已脱敏]`
- `Bearer <token>` → `Bearer [已脱敏]`
- `sk-` 开头的长 key → `sk-[已脱敏]`
- `-----BEGIN PRIVATE KEY-----` → `[已脱敏：私钥]`
- `-----BEGIN CERTIFICATE-----` → `[已脱敏：证书]`
- `.pfx` / `.pem` / `.key` 文件路径附近 → 路径保留，内容脱敏

## 不脱敏
- 命令本身（除非命令中明显带 secret）
- 非敏感输出如 "491 passed"
- 中文正常文案

## 集成点
- TaskClosureService.record_command()：redact command 和 result
- TaskClosureService.record_tool_result()：redact output
- ExecutionHandoffService.complete()/fail()：redact result
- ExecutionHandoffService.mark_bridge_failed()：redact bridge_error
- ExecutionAuditTimelineService：生成 summary 时对 command/result 脱敏

## 排除方案
- 不修改 shell_executor.py（保留既有 MAX_OUTPUT_BYTES 截断）
- 不拦截原始命令执行
- 不做通用 NLP/ML 敏感检测
