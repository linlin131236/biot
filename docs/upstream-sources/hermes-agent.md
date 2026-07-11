# Hermes Agent Upstream Source Record

## Fixed research source

| Field | Value |
| --- | --- |
| Repository | <https://github.com/NousResearch/hermes-agent> |
| Research commit | `291eae63b7d37129661082e23df35804c5e89365` |
| License | MIT |
| Purpose | Runtime contract and future ACP integration research |
| Copied source in Task 1 | None |

## Task 1 local implementation

`services/agent-core/src/bolt_core/runtime/` is an original Bolt-defined, runtime-neutral contract. It does not copy Hermes implementation code. It establishes the common interface boundary required before any Hermes ACP adapter is permitted.

## Required record for future source adaptation

Before copying or adapting any Hermes source, append an entry containing:

1. upstream repository path
2. exact upstream commit
3. applicable license and notice requirements
4. destination Bolt path
5. concise description of local modifications
6. focused test evidence
