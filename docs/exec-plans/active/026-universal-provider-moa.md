# Exec Plan 026 - Universal Provider System + MoA Mode

## Goal

Make Bolt capable of connecting to any OpenAI-compatible API endpoint and add an optional Mixture-of-Agents mode where several reference models answer in parallel and an aggregator model synthesizes the final answer.

This milestone is about provider flexibility, fallback reliability, usage attribution, and advanced model orchestration. It must not weaken permissions or make model choice affect tool safety.

## Why Now

Current model configuration is one provider at a time with a hardcoded `ModelConfig(provider, base_url, api_key, model, temperature)`. That blocks:

- Relay or proxy endpoints that are OpenAI-compatible.
- Switching providers mid-session.
- Ordered fallback when a provider rate-limits, times out, or overloads.
- MoA consultation for high-value planning or review tasks.
- Local cost accounting by provider, model, and task.

## Key Architecture Decisions

### Provider Registry

Add a registry loaded from `~/.bolt/providers.yaml` and environment variables. The registry stores provider metadata, model metadata, endpoint base URLs, extra headers, context windows, tool/streaming support, and pricing.

API keys are resolved at runtime from environment variable names. The YAML stores `api_key_env`, not raw secret values.

Any relay that exposes an OpenAI-compatible chat completions endpoint should work by adding provider configuration, without code changes.

### Multi-Provider Gateway

Replace single-provider client assumptions with a `MultiProviderGateway` that chooses the correct OpenAI-compatible client from the registry. Client instances can be cached per provider.

The gateway must preserve M19 behavior: function calling, streaming support where available, retry policy, timeout, and structured `ModelResponse`.

### Fallback Chain

Add a fallback wrapper around the multi-provider gateway. It tries the primary model first, then configured fallbacks only for transient failures such as rate limits, timeouts, or provider overload.

Fallback does not retry on permission denial, tool errors, malformed tool arguments, user cancellation, or safety failures.

### MoA Mode

MoA is optional and should be used for high-value synthesis tasks, not every step. Reference models run in parallel with the same prompt context. The aggregator receives attributed reference outputs and produces a final answer.

The aggregator must identify agreements, contradictions, and the reasoning it follows. It must not simply concatenate or average responses.

### Slash Commands

Add local slash commands that are processed before LLM routing:

- `/model` switches the active provider/model.
- `/fallback` shows or toggles fallback configuration.
- `/providers` lists configured providers and models.
- `/moa` runs an explicit MoA consultation.
- `/compact` triggers conversation compaction.
- `/plan` enters plan-only mode.
- `/diff` shows current git diff.
- `/review` reviews current changes.
- `/status` shows session, provider, token, permission, and budget state.
- `/cost` shows usage attribution.

### Cost Tracking

Add local usage records with provider, model, input tokens, output tokens, calculated cost, timestamp, and task attribution. Summaries should support total, per-model, per-task, and session budget views.

Goal Mode uses the same tracker for budget enforcement.

### Checkpointing

Add basic checkpoint save/resume for conversation history, memory state, agent tree, pending tasks, and current goal state. Conflict detection can be expanded in M27.

## Scope

- `provider_registry.py` for provider and model metadata.
- Multi-provider gateway support in `model_gateway.py`.
- `fallback_gateway.py` for ordered fallback.
- `moa_gateway.py` for reference-model parallelism and aggregator synthesis.
- `slash_commands.py` for local command handling.
- `cost_tracker.py` for usage attribution and budget checks.
- `checkpoint.py` for basic save/resume.
- API endpoints for providers, model switch, fallback, MoA, cost, checkpoints, and slash commands.
- Tests for registry loading, key resolution, base URL selection, fallback behavior, MoA prompt construction, cost accounting, checkpoint save/resume, and slash commands.

## Out of Scope

- Provider marketplace.
- Hosted account sync.
- Secret storage beyond environment variable resolution.
- Organization policy management.
- Automatic provider discovery from the internet.
- MoA for every agent step by default.
- Bypassing M19 tool-call and PermissionGate semantics.

## Safety Boundary

- API keys are never written to repo files.
- Provider YAML stores environment variable names, not key values.
- Cost tracking is local-only and has no external reporting.
- Fallback never bypasses PermissionGate.
- MoA reference calls run in the same process and same permission scope.
- MoA cost must be attributed to each reference model and the aggregator.
- Budget caps must stop or wrap up work before starting expensive new calls.
- Checkpoints may contain sensitive context and must live under `~/.bolt/checkpoints/` with restrictive permissions.
- Slash commands are local control commands, not untrusted prompt text.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_provider_registry_load_from_yaml`
   - `test_provider_registry_resolve_key_from_env`
   - `test_multi_provider_gateway_uses_correct_base_url`
   - `test_fallback_gateway_tries_next_on_rate_limit`
   - `test_fallback_gateway_does_not_retry_permission_denial`
   - `test_moa_gateway_runs_references_in_parallel`
   - `test_moa_gateway_builds_attributed_aggregator_prompt`
   - `test_cost_tracker_calculates_cost_from_pricing`
   - `test_cost_tracker_enforces_budget`
   - `test_checkpoint_save_and_resume`
   - `test_slash_command_model_switch`
   - `test_slash_command_moa_trigger`
3. `pnpm quality` passes.
4. Source files stay under 300 lines each.

## Acceptance Criteria

- [ ] `ProviderRegistry` loads providers from `~/.bolt/providers.yaml`.
- [ ] Provider keys resolve from environment variables at runtime.
- [ ] `MultiProviderGateway` can call any configured OpenAI-compatible endpoint.
- [ ] Fallback chain tries configured alternatives only for transient provider failures.
- [ ] MoA runs reference models in parallel and uses an aggregator to synthesize the final response.
- [ ] Slash commands exist for model, fallback, providers, MoA, compact, plan, diff, review, status, and cost.
- [ ] `CostTracker` records per-model usage and enforces session budget caps.
- [ ] Basic checkpoints can save and resume agent state.
- [ ] Provider fallback, MoA, and checkpoint resume keep the existing PermissionGate boundary.
- [ ] All tests pass and `pnpm quality` passes.
