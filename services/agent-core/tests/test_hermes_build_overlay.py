from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _builder():
    root = Path(__file__).parents[3]
    spec = spec_from_file_location("build_hermes_acp_runtime", root / "scripts" / "build-hermes-acp-runtime.py")
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_overlay_installs_only_the_core_owned_acp_model_client(tmp_path):
    builder = _builder()
    staging = tmp_path / "source"
    (staging / "acp_adapter").mkdir(parents=True)
    (staging / "agent").mkdir()
    (staging / "hermes_cli").mkdir()
    (staging / "setup.py").write_text('        *_data_file_tree("skills"),\n        *_data_file_tree("optional-skills"),\n', encoding="utf-8")
    (staging / "MANIFEST.in").write_text("graft skills\ngraft optional-skills\n", encoding="utf-8")
    (staging / "hermes_cli" / "config.py").write_text(
        '    merged = dict(client_kwargs.get("default_headers") or {})\n    merged.update(extra_headers)\n    client_kwargs["default_headers"] = merged\n',
        encoding="utf-8",
    )
    (staging / "acp_adapter" / "session.py").write_text(
        '        try:\n            runtime = resolve_runtime_provider(requested=requested_provider or config_provider)\n            kwargs.update(\n                {\n                    "provider": runtime.get("provider"),\n                    "api_mode": api_mode or runtime.get("api_mode"),\n                    "base_url": base_url or runtime.get("base_url"),\n                    "api_key": runtime.get("api_key"),\n                    "command": runtime.get("command"),\n                    "args": list(runtime.get("args") or []),\n                }\n            )\n        except Exception:\n            logger.debug("ACP session falling back to default provider resolution", exc_info=True)\n\n        _register_task_cwd(session_id, cwd)\n        agent = AIAgent(**kwargs)\n',
        encoding="utf-8",
    )
    (staging / "acp_adapter" / "server.py").write_text(
        'from acp_adapter.auth import TERMINAL_SETUP_AUTH_METHOD_ID, build_auth_methods, detect_provider\n'
        '        agent = state.agent\n        agent.tool_progress_callback = tool_progress_cb\n'
        '        except Exception:\n            logger.exception("Executor error for session %s", session_id)\n            with state.runtime_lock:\n                state.is_running = False\n                state.current_prompt_text = ""\n            return PromptResponse(stop_reason="end_turn")\n\n        if result.get("messages"):\n',
        encoding="utf-8",
    )
    (staging / "agent" / "chat_completion_helpers.py").write_text(
        '            elif agent.provider == "moa":\n                # MoA is a virtual chat-completions provider backed by the\n                # in-process MoAClient facade. Do not rebuild a request-local\n                # OpenAI client from the virtual runtime metadata.\n                result["response"] = agent.client.chat.completions.create(**api_kwargs)\n            else:\n',
        encoding="utf-8",
    )

    changes = builder._apply_bolt_overlay(staging)

    assert (staging / "acp_adapter" / "bolt_model_client.py").is_file()
    assert "bolt-managed" in (staging / "acp_adapter" / "session.py").read_text(encoding="utf-8")
    assert "bind_bolt_model_client" in (staging / "acp_adapter" / "server.py").read_text(encoding="utf-8")
    assert 'agent.provider in {"moa", "bolt-acp"}' in (
        staging / "agent" / "chat_completion_helpers.py"
    ).read_text(encoding="utf-8")
    assert {item["path"] for item in changes} >= {
        "acp_adapter/bolt_model_client.py",
        "acp_adapter/session.py",
        "acp_adapter/server.py",
        "agent/chat_completion_helpers.py",
    }
