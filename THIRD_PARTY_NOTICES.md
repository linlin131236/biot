# Third-Party Notices

## Hermes Agent

- Repository: <https://github.com/NousResearch/hermes-agent>
- Fixed source commit: `291eae63b7d37129661082e23df35804c5e89365`
- License: MIT; distributed text: `services/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/licenses/HERMES-AGENT-MIT.txt`
- Distributed scope: headless ACP runtime bundle only. Dashboard, TUI, installer, bundled skills, and optional skills are excluded.
- Provenance and all bundled file hashes: `services/agent-core/src/bolt_core/runtime-releases/hermes/0.18.2/metadata/provenance.json` and `services/agent-core/src/bolt_core/runtime/hermes_release_inventory.py`.
- Local distribution overlays: exclude the `skills/` and `optional-skills/` data trees; allow an explicitly empty custom-provider `Authorization` field to suppress the OpenAI SDK bearer header when the only permitted endpoint is Bolt's loopback model proxy. Exact upstream file hashes and rationale are in provenance.
- Additional retained notices: Apache-2.0 `plugins/security-guidance` license/notice and MIT `plugins/hermes-achievements` license are copied under the bundle `licenses/` directory.

The bundled Hermes runtime remains unavailable for task execution until Bolt can verify an OS-enforced workspace projection. Bolt does not inject provider API keys into this runtime.
