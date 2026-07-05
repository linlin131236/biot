# Exec Plan 026 - Universal Provider System + MoA Mode

## Goal

Make Bolt capable of connecting to ANY OpenAI-compatible API endpoint (中转站/relay/proxy/direct), and add a Mixture-of-Agents (MoA) mode where multiple models consult in parallel and a stronger model aggregates the final answer.

## Why Now

Bolt's current `ModelSettingsStore` only supports one provider at a time with a hardcoded `ModelConfig(provider, base_url, api_key, model, temperature)`. This cannot:
- Connect to Chinese relay stations (中转站) like Zyloo, APIKEY.FUN, DeepSeek direct
- Switch providers mid-task
- Run MoA (multiple models consulting + aggregator裁决)
- Fall back to a cheaper model when rate-limited

Codex and Claude Code both support multi-provider + fallback in 2026. Bolt needs the same.

## Architecture

```
Provider Registry (YAML/JSON config)
├── zyloo:        { api: https://api.zyloo.io/v1, key: $ZYLOO_API_KEY }
├── deepseek:     { api: https://api.deepseek.com/v1, key: $DEEPSEEK_API_KEY }
├── openai:       { api: https://api.openai.com/v1, key: $OPENAI_API_KEY }
├── local-ollama: { api: http://localhost:11434/v1, key: none }
└── custom-relay: { api: https://any-relay.example.com/v1, key: xxx }

Model Selection
├── Direct mode:  pick one provider + model → single LLM call
├── Fallback mode: primary → fallback1 → fallback2 (on rate-limit/error)
└── MoA mode:     reference models (parallel) → aggregator (裁决)
```

## Scope

### 1. Provider Registry

New file: `services/agent-core/src/bolt_core/provider_registry.py`

```python
@dataclass
class ProviderConfig:
    name: str           # "zyloo"
    api_base: str       # "https://api.zyloo.io/v1"
    api_key_env: str    # "ZYLOO_API_KEY" — env var name, not the key itself
    api_key: str | None # resolved at runtime from env or manual input
    models: dict[str, ModelInfo]  # model_id → {context, name, pricing}
    headers: dict[str, str]       # extra headers (some relays need custom auth)

@dataclass
class ModelInfo:
    id: str             # "zyloo/claude-sonnet-5"
    display_name: str   # "Claude Sonnet 5 (Zyloo)"
    context_window: int # 200000
    input_price: float  # $/1M tokens
    output_price: float # $/1M tokens
    supports_tools: bool = True
    supports_streaming: bool = True

class ProviderRegistry:
    def __init__(self, config_path: str = "~/.bolt/providers.yaml"):
        # Load from YAML, merge with env vars
        pass
    
    def get(self, provider_name: str) -> ProviderConfig
    def list(self) -> list[ProviderConfig]
    def resolve_key(self, provider_name: str) -> str | None
    def add(self, config: ProviderConfig) -> None
    def remove(self, provider_name: str) -> None
    def model_config(self, provider: str, model: str) -> ModelConfig
```

Provider config file `~/.bolt/providers.yaml`:

```yaml
providers:
  zyloo:
    api_base: https://api.zyloo.io/v1
    api_key_env: ZYLOO_API_KEY
    models:
      zyloo/claude-sonnet-5:
        display_name: "Claude Sonnet 5 (Zyloo)"
        context_window: 200000
        input_price: 3.0
        output_price: 15.0
      zyloo/gpt-4o:
        display_name: "GPT-4o (Zyloo)"
        context_window: 128000
        input_price: 2.5
        output_price: 10.0
  deepseek:
    api_base: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
    models:
      deepseek-chat:
        display_name: "DeepSeek V3"
        context_window: 65536
        input_price: 0.27
        output_price: 1.10
      deepseek-reasoner:
        display_name: "DeepSeek R1"
        context_window: 65536
        input_price: 0.55
        output_price: 2.19
  local-ollama:
    api_base: http://localhost:11434/v1
    api_key_env: ""
    models:
      local/qwen3-coder:
        display_name: "Qwen3 Coder (Local)"
        context_window: 131072
        input_price: 0.0
        output_price: 0.0
  custom:
    api_base: ""   # user fills in any relay URL
    api_key_env: CUSTOM_API_KEY
    models: {}     # user adds models manually
```

**Key design**: Any relay station that exposes an OpenAI-compatible `/chat/completions` endpoint works. Just add `api_base` + `api_key_env` + models. Zero code change needed for new relays.

### 2. Multi-Provider ModelGateway

Update file: `services/agent-core/src/bolt_core/model_gateway.py`

```python
class MultiProviderGateway:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self._clients: dict[str, openai.OpenAI] = {}
    
    def complete(self, request: ModelRequest) -> ModelResponse:
        provider = request.config.provider
        client = self._get_client(provider)
        # Use openai SDK with custom base_url + api_key from registry
        # Supports function calling, streaming, retries
    
    def _get_client(self, provider: str) -> openai.OpenAI:
        if provider not in self._clients:
            config = self.registry.get(provider)
            self._clients[provider] = openai.OpenAI(
                base_url=config.api_base,
                api_key=config.api_key or "not-needed",
            )
        return self._clients[provider]
```

### 3. Fallback Model Chain

Inspired by Claude Code's `fallbackModel` (June 2026).

New file: `services/agent-core/src/bolt_core/fallback_gateway.py`

```python
@dataclass
class FallbackEntry:
    provider: str
    model: str
    max_tokens: int = 4096
    cost_ceiling: float = 1.0   # $ max spend before falling through
    timeout_seconds: int = 120

class FallbackGateway:
    def __init__(self, gateway: MultiProviderGateway, fallbacks: list[FallbackEntry]):
        self.gateway = gateway
        self.fallbacks = fallbacks
    
    def complete(self, request: ModelRequest) -> ModelResponse:
        # Try primary model first
        response = self.gateway.complete(request)
        if response.status == "completed":
            return response
        if response.error in ("rate_limit", "timeout", "model_overloaded"):
            # Try fallbacks in order
            for fallback in self.fallbacks:
                fallback_config = self.registry.model_config(fallback.provider, fallback.model)
                fallback_request = ModelRequest(request.messages, fallback_config)
                response = self.gateway.complete(fallback_request)
                if response.status == "completed":
                    return response
        return response  # all failed, return last error
```

Config in `~/.bolt/settings.yaml`:

```yaml
model:
  provider: zyloo
  model: zyloo/claude-sonnet-5
  fallback:
    - provider: deepseek
      model: deepseek-chat
      cost_ceiling: 0.50
    - provider: local-ollama
      model: local/qwen3-coder
      cost_ceiling: 0.00
```

### 4. MoA Mode (Mixture of Agents)

Inspired by Hermes MoA. Multi-expert consultation + aggregator裁决.

New file: `services/agent-core/src/bolt_core/moa_gateway.py`

```python
@dataclass
class MoAReferenceModel:
    provider: str
    model: str
    temperature: float = 0.6

@dataclass
class MoAConfig:
    reference_models: list[MoAReferenceModel]
    aggregator_provider: str
    aggregator_model: str
    aggregator_temperature: float = 0.4
    max_tokens: int = 4096

class MoAGateway:
    def __init__(self, gateway: MultiProviderGateway):
        self.gateway = gateway
    
    def complete(self, request: ModelRequest, moa_config: MoAConfig) -> MoAResponse:
        # Phase 1: Run reference models in PARALLEL
        reference_responses = self._run_references(request, moa_config)
        
        # Phase 2: Build aggregator prompt with all reference responses
        aggregator_request = self._build_aggregator_request(
            request, reference_responses, moa_config
        )
        
        # Phase 3: Aggregator裁决
        aggregator_response = self.gateway.complete(aggregator_request)
        
        return MoAResponse(
            final=aggregator_response,
            references=reference_responses,
        )
```

Aggregator system prompt:
```
You are an aggregator in a Mixture-of-Agents system. Multiple expert models have independently answered the same question. Your job is to synthesize their responses into the best possible final answer.

## Expert Responses
{reference_responses with model attribution}

## Rules
1. Identify agreements across experts — these are likely correct.
2. Identify contradictions — analyze which expert's reasoning is more sound.
3. Do NOT simply average or merge. Pick the best reasoning and build on it.
4. If all experts agree, strengthen the conclusion with additional detail.
5. Cite which expert(s) you're following for each key point.
6. Produce the final answer.
```

Config in `~/.bolt/settings.yaml`:

```yaml
moa:
  enabled: true
  reference_models:
    - provider: deepseek
      model: deepseek-chat
      temperature: 0.6
    - provider: zyloo
      model: zyloo/gpt-4o
      temperature: 0.6
  aggregator:
    provider: zyloo
    model: zyloo/claude-sonnet-5
    temperature: 0.4
```

### 5. Slash Commands (Codex-style)

New file: `services/agent-core/src/bolt_core/slash_commands.py`

Inspired by Codex's slash command system. Processed locally, not sent to LLM.

```python
class SlashCommandHandler:
    def handle(self, command: str, args: str, harness: Harness) -> SlashResult:
        # /model zyloo/claude-sonnet-5  → switch model
        # /moa <question>               → trigger MoA mode
        # /fallback                     → toggle fallback chain
        # /providers                    → list available providers
        # /compact                      → summarize conversation
        # /plan <description>           → switch to plan-only mode
        # /diff                         → show git diff
        # /review                       → review current changes
        # /status                       → show session info (model, tokens, cost)
        # /cost                         → show usage attribution breakdown
```

| Command | Purpose | Inspired by |
|---|---|---|
| `/model <provider/model>` | Switch active model | Codex `/model` |
| `/moa <question>` | Trigger MoA consultation + aggregation | Hermes MoA |
| `/fallback` | Toggle fallback chain on/off | Claude Code `fallbackModel` |
| `/providers` | List configured providers + models | Codex `/status` |
| `/compact` | Summarize conversation to free context | Codex `/compact` |
| `/plan <desc>` | Plan-only mode (read + plan, no writes) | Codex `/plan` |
| `/diff` | Show git diff of agent changes | Codex `/diff` |
| `/review` | Review working tree changes | Codex `/review` |
| `/status` | Session info: model, tokens, cost, permissions | Codex `/status` |
| `/cost` | Usage attribution breakdown by model | Claude Code `--attribution` |

### 6. Usage Attribution + Cost Tracking

Inspired by Claude Code's `--attribution` (June 2026).

New file: `services/agent-core/src/bolt_core/cost_tracker.py`

```python
@dataclass
class UsageRecord:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: str
    task: str        # which agent step or MoA phase

class CostTracker:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self.records: list[UsageRecord] = []
    
    def record(self, provider: str, model: str, usage: TokenUsage, task: str) -> UsageRecord:
        # Calculate cost from registry pricing
        info = self.registry.get(provider).models.get(model)
        cost = (usage.input_tokens / 1_000_000 * info.input_price) + \
               (usage.output_tokens / 1_000_000 * info.output_price)
        record = UsageRecord(provider, model, usage.input_tokens, usage.output_tokens, cost, _now(), task)
        self.records.append(record)
        return record
    
    def summary(self) -> CostSummary:
        # Total cost, per-model breakdown, per-task breakdown
        pass
    
    def check_budget(self, max_cost: float) -> bool:
        return sum(r.cost for r in self.records) < max_cost
```

API endpoints:
- `GET /cost/summary` — total cost, per-model, per-task
- `GET /cost/records` — detailed usage log
- `POST /cost/budget` — set session budget cap

### 7. Agent Checkpointing

Inspired by Claude Code's `checkpoint save/resume` (June 2026 beta).

New file: `services/agent-core/src/bolt_core/checkpoint.py`

```python
class CheckpointManager:
    def save(self, run_id: str, name: str) -> CheckpointResult:
        # Save: conversation history, memory state, agent tree, pending tasks
        # Write to ~/.bolt/checkpoints/{name}/
    
    def resume(self, name: str) -> HarnessRun:
        # Restore full state from checkpoint
        # Detect file conflicts (files changed externally since save)
    
    def list(self) -> list[CheckpointInfo]:
        pass
    
    def delete(self, name: str) -> None:
        pass
```

### 8. API Endpoints

File: `services/agent-core/src/bolt_core/app.py`

New endpoints:
- `GET /providers` — list providers
- `POST /providers` — add provider
- `DELETE /providers/{name}` — remove provider
- `GET /providers/{name}/models` — list models for provider
- `POST /model/switch` — switch active model
- `POST /model/fallback` — configure fallback chain
- `POST /moa/run` — trigger MoA consultation
- `GET /moa/config` — get MoA config
- `POST /moa/config` — update MoA config
- `GET /cost/summary` — cost breakdown
- `GET /cost/records` — detailed usage log
- `POST /cost/budget` — set budget cap
- `POST /checkpoints/save` — save checkpoint
- `POST /checkpoints/{name}/resume` — resume from checkpoint
- `GET /checkpoints` — list checkpoints
- `POST /slash` — process slash command

## Safety Boundary

- API keys are resolved from environment variables at runtime, never stored in YAML files.
- Provider YAML only stores `api_key_env: ZYLOO_API_KEY` (the env var name), not the key itself.
- Cost tracking is local-only, no external reporting.
- MoA runs reference models in parallel threads, same process, same permission scope.
- Fallback chain does not bypass PermissionGate.
- Checkpoints may contain sensitive context; stored in `~/.bolt/checkpoints/` with 700 permissions.

## Verification

1. All existing tests pass (new providers are additive, FakeModelGateway still works for tests).
2. New tests:
   - `test_provider_registry_load_from_yaml`
   - `test_provider_registry_resolve_key_from_env`
   - `test_multi_provider_gateway_uses_correct_base_url`
   - `test_fallback_gateway_tries_next_on_rate_limit`
   - `test_moa_gateway_runs_references_in_parallel`
   - `test_moa_gateway_builds_aggregator_prompt`
   - `test_cost_tracker_calculates_cost_from_pricing`
   - `test_cost_tracker_enforces_budget`
   - `test_checkpoint_save_and_resume`
   - `test_slash_command_model_switch`
   - `test_slash_command_moa_trigger`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `ProviderRegistry` loads from `~/.bolt/providers.yaml`, resolves keys from env.
- [ ] `MultiProviderGateway` connects to any OpenAI-compatible endpoint.
- [ ] `FallbackGateway` chains primary → fallback1 → fallback2 on errors.
- [ ] `MoAGateway` runs reference models in parallel, aggregator synthesizes.
- [ ] Slash commands: `/model`, `/moa`, `/fallback`, `/providers`, `/status`, `/cost`, `/compact`, `/plan`, `/diff`, `/review`.
- [ ] `CostTracker` with per-model pricing, session budget enforcement.
- [ ] `CheckpointManager` save/resume agent state.
- [ ] All tests pass. Source files under 300 lines.
- [ ] Any relay station with OpenAI-compatible API works by adding YAML config, zero code change.
