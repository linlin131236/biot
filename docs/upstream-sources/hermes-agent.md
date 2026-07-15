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

## Task 2 distributed headless ACP artifact

Bolt distributes a fixed Windows x64 headless ACP runtime under `services/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/`. The catalog-owned inventory is generated in `services/agent-core/src/bolt_core/runtime/hermes_release_inventory.py`; it hashes every payload file, including licenses and `metadata/provenance.json`. The payload contains a payload-local CPython 3.11.15 launcher and must run only as:

```text
bin/hermes-acp.exe -I -B -m acp_adapter.entry
```

It is built from the fixed research commit using the upstream `uv.lock`; the result is a non-editable wheel installation whose `acp_adapter`, `hermes_cli`, and `run_agent` imports resolve only from payload `Lib/site-packages`. The bundle does not include the upstream Dashboard, TUI, installer, `skills/`, or `optional-skills/` trees. Excluding those data trees is required for headless ACP scope and avoids redistribution of `skills/productivity/powerpoint`, whose bundled license forbids copying and distribution.

The artifact makes three scoped modifications in a disposable build copy only. `setup.py` and `MANIFEST.in` omit the two excluded data trees. `hermes_cli/config.py` changes an explicitly empty named-custom-provider `Authorization` header into an empty OpenAI SDK API key, so the SDK emits no `Authorization` header while the configuration supplies only `X-Bolt-Runtime-Token` to Bolt's loopback proxy. No provider API key is placed in the runtime configuration, environment beyond the temporary runtime token, log, database, or artifact. Exact before/after hashes and the build input hashes are in bundle provenance.

The artifact includes the upstream MIT license plus the retained Apache-2.0 `plugins/security-guidance` license/notice and MIT `plugins/hermes-achievements` license under `licenses/`. It remains installable but non-startable until a separately verified Windows OS-enforced workspace projection exists; `cwd`, a copied directory, or read-only attributes do not satisfy that gate.


## Task 2 original Bolt adapter

The following Bolt files are original implementations. No Hermes source was copied:

- `services/agent-core/src/bolt_core/runtime/hermes_manifest.py`
- `services/agent-core/src/bolt_core/runtime/hermes_installer.py`
- `services/agent-core/src/bolt_core/runtime/hermes_acp.py`
- `services/agent-core/src/bolt_core/runtime/acp_events.py`
- `services/agent-core/src/bolt_core/runtime/acp_stdio.py`

Protocol and isolation evidence reviewed against `291eae63b7d37129661082e23df35804c5e89365`:

- Hermes starts ACP with `hermes acp`, `hermes-acp`, or `python -m acp_adapter.entry`; ACP is stdio JSON-RPC and keeps logs on stderr.
- Verified lifecycle methods are `initialize`, `session/new`, `session/load`, `session/prompt`, and `session/cancel`; permission callbacks use ACP `session/request_permission`.
- Initialize identifies `hermes-agent`, returns ACP protocol version 1, and advertises `loadSession`; Bolt validates all three before accepting a session.
- Upstream `resume_session` creates a new Hermes session when missing, so Bolt uses only `session/load` for a locally mapped session and rejects a missing local mapping.
- `HERMES_HOME` changes the Hermes configuration home. Bolt creates one isolated home per Runtime Session and writes `memory.provider: ''` plus `plugins.enabled: []` to disable external memory providers and optional plugins.
- Upstream Windows desktop teardown uses `taskkill /PID <pid> /T /F`; Bolt uses the same argument-array tree termination pattern after ACP cancel timeout.

The original task handoff listed `91eae63b7d37129661082e23df35804c5e89365`. That is not a valid local Git object; the project design, upstream record, and verified object use `291eae63b7d37129661082e23df35804c5e89365`.

Focused evidence: `tests/test_hermes_manifest.py`, `tests/test_hermes_acp_runtime.py`, `tests/test_acp_events.py`, and `tests/test_hermes_acp_integration.py`. The first three use a deterministic fake ACP agent. The real integration test is intentionally not considered passing without a supplied, managed installation of the fixed Hermes commit.

## Required record for future source adaptation

Before copying or adapting any Hermes source, append an entry containing:

1. upstream repository path
2. exact upstream commit
3. applicable license and notice requirements
4. destination Bolt path
5. concise description of local modifications
6. focused test evidence
