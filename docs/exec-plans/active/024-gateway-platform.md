# Exec Plan 024 - Gateway Platform Integration

## Goal

Connect Bolt to messaging platforms (Feishu, Telegram, Discord) via a Gateway, enabling remote interaction from phone/desktop without opening the Bolt desktop app.

## Why Now

After Plans 019-023, Bolt is a fully functional conversational coding agent. But you can only use it at your desk. Gateway integration means you can message Bolt from your phone via Feishu/Telegram, just like Hermes.

## Architecture

```
User (Feishu/Telegram/Discord)
    ↓ message
Gateway (WebSocket/HTTP long-poll)
    ↓ route to
Bolt Agent Core API (localhost)
    ↓ response
Gateway
    ↓ deliver
User
```

## Scope

### 1. Gateway adapter interface

New file: `services/agent-core/src/bolt_core/gateway.py`

```python
class GatewayAdapter(Protocol):
    def start(self, conversation_handler: Callable) -> None: ...
    def stop(self) -> None: ...
    def send(self, conversation_id: str, message: str) -> None: ...

class GatewayManager:
    def __init__(self):
        self.adapters: dict[str, GatewayAdapter] = {}
    
    def register(self, platform: str, adapter: GatewayAdapter) -> None: ...
    def start_all(self, handler) -> None: ...
    def stop_all(self) -> None: ...
```

### 2. Feishu adapter

New file: `services/agent-core/src/bolt_core/gateways/feishu.py`

- Uses Feishu Bot SDK (or raw HTTP + WebSocket).
- Receives messages → creates/continues Bolt conversation → sends response.
- Supports rich messages (code blocks, diffs, file attachments).

### 3. Telegram adapter

New file: `services/agent-core/src/bolt_core/gateways/telegram.py`

- Uses python-telegram-bot or raw HTTP long-poll.
- Same flow as Feishu.

### 4. Gateway configuration

File: `services/agent-core/src/bolt_core/gateway_config.py`

```python
@dataclass
class GatewayConfig:
    feishu: FeishuConfig | None = None
    telegram: TelegramConfig | None = None
    
@dataclass
class FeishuConfig:
    app_id: str
    app_secret: str
    verification_token: str
    
@dataclass  
class TelegramConfig:
    bot_token: str
```

Load from `~/.bolt/gateway.yaml` or environment variables.

### 5. API endpoints

- `GET /gateway/status` — which platforms are connected
- `POST /gateway/start` — start gateway for a platform
- `POST /gateway/stop` — stop gateway
- `GET /gateway/conversations` — list active remote conversations

### 6. Permission flow over messaging

- Pending permissions show as interactive buttons (approve/reject) in Feishu/Telegram.
- If platform doesn't support buttons, permission defaults to "deny" (safe default).

## Safety Boundary

- Gateway is opt-in (must configure credentials).
- All remote conversations still go through PermissionGate.
- No workspace access without explicit user approval (same as desktop).
- Gateway credentials stored locally, never in repo.
- Rate limiting: max 10 messages per minute per conversation.

## Verification

1. All existing tests pass (gateway is additive).
2. New tests with mocked platform APIs:
   - `test_feishu_adapter_receives_and_responds`
   - `test_telegram_adapter_receives_and_responds`
   - `test_gateway_manager_start_stop`
   - `test_permission_buttons_rendered_in_feishu`
3. Manual smoke test with real Feishu bot (documented).

## Acceptance Criteria

- [ ] `GatewayAdapter` protocol and `GatewayManager`.
- [ ] Feishu adapter with message receive/respond.
- [ ] Telegram adapter with message receive/respond.
- [ ] Permission approval via interactive buttons.
- [ ] Gateway configuration from YAML/env.
- [ ] API endpoints for gateway management.
- [ ] All tests pass.
