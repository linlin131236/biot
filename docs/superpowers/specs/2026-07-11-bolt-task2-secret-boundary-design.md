# Bolt Task 2 Secret Boundary Design

## 状态与范围

- 日期：2026-07-11
- 分支：`feat/safe-controlled-beta`
- 状态：用户已批准执行
- 目标：关闭 Task 2 非敏感 SQLite 持久化核心的 Secret 绕过 P0。
- 范围内：持久化值验证、Repository 写入口、message/checkpoint 基础方法、磁盘 canary 测试。
- 范围外：Harness/会话/任务业务接线、旧 SQLite/JSON 迁移、Task 3 模型设置接线、Task 4 真相源收敛。

## 根因

当前 `validate_json_object` 仅对 key 执行 `lower()`，并使用有限精确黑名单；`apiKey`、`x-api-key`、`password`、`headers`、`privateKey` 等可绕过。字符串只检测 `authorization:`、`bearer ` 与 `sk-`，URL query 和其他常见凭据格式可绕过。`model_profiles.base_url` 等普通文本列不经过 JSON 验证器，因此即使扩充 JSON 黑名单，Repository 仍可能写入 Secret。

## 选定方案

采用五层防御：

1. **键名规范化**：NFKC + casefold + 去除非字母数字分隔符。规范键只要包含 `token` 就默认拒绝，仅精确允许 `token_count`、`max_tokens`、input/output/total token usage 等计数字段；`token_value` 等不得依赖前后缀猜测。
2. **结构化值检测**：拒绝 NUL、私钥头、Authorization header/assignment、敏感赋值键与明确凭据前缀。裸 `Basic`/`Bearer` 只在整个值符合“scheme + 单个 credential token”结构时拒绝，普通英文句子必须允许。
3. **字段级策略**：workspace path、identifier/status、provider/model、message content、credential reference、JSON value 和 URL 使用独立验证函数。不得再把所有字符串交给同一个启发式函数。
4. **URL 专用验证**：只接受 `http`/`https`，拒绝 userinfo、fragment、控制字符、空白/非法 host 和非法端口。`netloc` 或 query key 出现 percent encoding 时直接 fail closed；query value 可以编码，但 query key 不做任意轮数解码。
5. **Repository 全入口**：所有 JSON 字段走同一递归边界；所有直接文本列按字段策略验证。新增 message metadata 与 checkpoint payload 的 Repository 基础方法，但不接入业务层。

黑名单不能识别任意随机字符串是否是 Secret，因此不宣称“万能检测”。安全保证来自字段级允许策略、Token usage 明确白名单、禁止敏感键族、受限 URL、结构化凭据模式、Repository 唯一写边界和磁盘 canary 联合防御。

## 第三次失败后的架构门禁

同一 Secret 边界连续三轮被相邻输入绕过后，停止继续增加正则或解码轮数。禁止以下做法：

- 用 `endswith("token")` 代替 Token 字段策略。
- 用固定 2/3/5 次 `unquote` 对抗任意层编码。
- 用字符串长度判断所有 Basic/Bearer 文本。
- 用一个 `validate_non_sensitive_text` 同时验证路径、消息和模型标识符。

重设计后的实现必须让“策略选择”发生在 Repository 字段边界，而不是让通用字符串扫描器猜字段语义。

## 数据流

```text
业务/测试输入
  -> Repository 结构化方法
      -> 文本字段专用验证
      -> JSON 递归 SecretBoundary
      -> 显式事务
      -> SQLite / WAL
      -> SQLite backup
```

验证必须在开启写事务之前完成，异常消息只能包含字段类别，不能回显原始值。

## Repository API

- `save_workspace(...)`：使用 workspace path 策略，不因正常 `risk-*` 路径误杀。
- `create_task(..., payload)`：identifier 策略 + `payload_json` 递归策略。
- `append_runtime_event(..., payload)`：identifier 策略 + `payload_json` 递归策略。
- `append_message(..., metadata)`：identifier、message content 与 `metadata_json` 三种策略。
- `save_checkpoint(..., payload)`：验证 `payload_json`。
- `save_model_profile(...)` / `update_model_profile(...)`：分别验证 `config_json`、严格 `base_url`、provider/model identifier 与 credential reference。

## 测试设计

RED 必须覆盖：

- key 变体：`apiKey`、`x-api-key`、`password`、`headers.Cookie`、`privateKey`、嵌套/list 内敏感键。
- value 变体：Authorization、私钥头、`password=...`、`access_token=...`、常见 API Key 前缀。
- URL：userinfo、`access_token`/`api_key`/`password` query、fragment、非 HTTP(S)。
- URL 邻接攻击：编码 userinfo、任意多层编码 query key、含空格 host、非法端口；策略必须 fail closed，不能依赖解码轮数。
- Token 邻接攻击：`token_value`、`tokenValue` 必须拒绝，`token_count`、`max_tokens` 必须允许。
- 合法文本：`risk-management` 路径、`Basic configuration guide` 消息、`risk-model` provider/model 必须允许。
- 四类 JSON 字段：task、runtime event、message metadata、checkpoint payload。
- model profile 的直接文本列与 update 路径。
- 异常和日志不包含 canary。
- 被拒绝后，SQLite 主库、WAL、SHM、所有 backup 都不包含 canary 字节。

## 失败处理

- 敏感或结构不合法：抛出稳定 `ValueError`，不回显输入。
- 验证失败：不得进入事务，不产生部分行。
- 三次修复仍出现同类绕过：停止补词，回到字段 schema/数据模型重新设计。

## 验收门禁

- 新增测试先 RED、实现后 GREEN。
- Task 2 focused 全绿。
- Python 编译、架构门禁、后端全量、Desktop 全量与构建完成。
- 独立规格审查和代码质量审查无 P0/P1。
- `git diff --check` 通过。
- Task 2 只可宣称“统一持久化基础设施完成”，不得宣称 Task 4 业务真相源已收敛。
