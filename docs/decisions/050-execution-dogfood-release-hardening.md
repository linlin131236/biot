# Decision 050: End-to-End Dogfood and Release Hardening

## Decision
Validate the M48-M49 permission-gated execution flow with an end-to-end backend dogfood test and release hardening checks, without introducing new runtime capabilities.

## Rationale
M48 created pending permissions from approved handoffs, and M49 ingested results after existing PermissionGate approval. M50 proves the complete loop works as a product flow before any push or release: missing evidence produces a verification queue item, human approval creates a handoff, request-permission creates pending permission, user approval executes through the existing path, and ingestion records evidence for assessment.

## Rules
- No automatic approve.
- No PermissionGate bypass.
- No new shell execution path.
- No goal creation or Agent Loop start in the dogfood chain.
- No release, tag, push, delete, or generated artifact staging.
- Completion remains evidence-based through the existing assessment API.

## Safety
The e2e test patches the executor only to make the test deterministic while still exercising the existing approve_permission endpoint. Product code continues to execute only after a pending permission is approved through PermissionGate.
