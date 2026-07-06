# M31 Integration Smoke

## Status

Accepted.

## Context

The autonomous platform baseline introduced goal mode, conversations, vector memory, skills, delegation, provider policy, MoA, checkpoints, review gate, and desktop autonomy client types. Most pieces had unit coverage, but the product needed a single integration smoke proving that core routes and desktop client methods agree on the same runtime contract.

Checkpoint and review gate services already existed. The desktop client had methods for them, but those methods intentionally threw because no backend route was registered.

## Decision

M31 wires only the existing checkpoint and review gate services:

- `POST /checkpoints` creates a checkpoint.
- `GET /checkpoints/{checkpoint_id}` loads a checkpoint.
- `POST /review/evaluate` evaluates checklist items against recorded boolean results.
- `harnessClientAutonomy.ts` calls those real endpoints.

Checkpoint creation follows the run workspace when a known `run_id` is provided. The process keeps an in-memory checkpoint-to-workspace map so a checkpoint created during a smoke session can be loaded without the caller repeating the workspace.

The `/skills` surface remains explicitly unwired until a backend route exists. M31 does not pretend a route exists by returning fake data.

## Consequences

The baseline now has a narrow end-to-end smoke path from desktop API client to Agent Core. This reduces the risk that future phases add isolated modules without a working product path.

M31 does not add new autonomous behavior, automatic phase continuation, release packaging, publishing, signing, or online updates.
