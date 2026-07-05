# M29 Agent Product Convergence

## Status

Accepted.

## Context

M19-M28 describe the path from Bolt's safe skeleton to a real coding agent: real LLM tool calling, expanded tools, vector memory, delegation, conversations, gateways, skills, provider flexibility, intelligent workflow features, and Goal Mode.

The original sequence leaves Goal Mode until M28. That makes the most important product loop arrive late, after many capabilities already exist. Modern coding agents show a stronger pattern: durable objectives, audit trails, scoped tools, skills, subagents, and resumable long-running work should converge around a persistent task loop.

## Decision

Bolt will treat Goal Mode as the long-task control plane and pull its foundation forward. The implementation roadmap is reordered as:

1. M19 Real LLM Integration, with minimal Goal state and evidence primitives.
2. M20 Core Tool Expansion, wired into Goal evidence and verification.
3. M23 Multi-Turn Conversation, auto-compact, and Goal persistence.
4. M26 provider registry, fallback, slash commands, and cost tracking.
5. M25 Skill System.
6. M21 Vector Memory.
7. M22 Multi-Agent Delegation with templates and scoped permissions.
8. M24 Gateway Platform Integration.
9. Remaining M28 Goal lifecycle UI and controls.
10. Remaining M27 intelligent features and M26 advanced MoA/checkpoint work.

Goal Mode becomes the hub that other features must serve. Tools produce evidence for goals. Conversations preserve goals. Providers enforce budgets for goals. Skills guide goals. Memory retrieves context for goals. Subagents help goals. Gateways and automations expose goals remotely.

## Safety Decision

The consolidation does not relax Bolt's safety model:

- PermissionGate remains the execution choke point.
- Writes require diff confirmation.
- Shell and terminal actions require confirmation unless a future explicit auto-approve mode is separately designed.
- Completion claims require concrete evidence.
- Provider fallback, skills, memory, gateways, and subagents cannot bypass parent scope.
- Credentials, memory, checkpoints, and traces stay local by default.

## Consequences

M29 supersedes the raw M19-M28 ordering without deleting those plans. Future implementation should start from the revised sequence in the M29 roadmap, not from the numeric order alone.

This decision keeps M19 as the next implementation entry point, but prevents it from being a narrow LLM plumbing task. M19 should establish the response shape and loop semantics that Goal Mode will later expand.

This decision also delays flashy capabilities until the durable loop is ready. MoA, gateways, multi-repo work, hooks, and advanced checkpoints remain valuable, but they should not precede the product's ability to preserve objectives, record evidence, stop safely, and resume.
