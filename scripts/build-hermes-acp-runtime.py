"""Build the fixed, headless Hermes ACP runtime bundle for Bolt.

This script intentionally accepts no development venv, PATH executable, user
Hermes home, or editable installation as an input. It rebuilds the pinned
upstream source into a self-contained CPython prefix and produces the catalog
inventory consumed by ``HermesReleaseCatalog``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable


UPSTREAM_COMMIT = "291eae63b7d37129661082e23df35804c5e89365"
VERSION = "0.18.2"
SOURCE_URL = "https://github.com/NousResearch/hermes-agent"
DEFAULT_SOURCE = Path(r"D:\bolt\build\upstream\hermes-291eae63")
DEFAULT_PYTHON = Path(
    r"C:\Users\bi240\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe"
)
DEFAULT_OUTPUT = Path(
    r"D:\bolt\Bolt\services\agent-core\src\bolt_core\runtime-releases\hermes\0.18.2"
)
DEFAULT_BUILD_ROOT = Path(r"D:\bolt\build\hermes-acp-0.18.2")
DEFAULT_CATALOG_OUTPUT = Path(
    r"D:\bolt\Bolt\services\agent-core\src\bolt_core\runtime\hermes_release_inventory.py"
)

_EXCLUDED_SOURCE_DIRS = {"skills", "optional-skills"}
_SENSITIVE_ENV_PARTS = ("API_KEY", "AUTHORIZATION", "CREDENTIAL", "SECRET", "TOKEN")
_SCRUBBED_ENV_NAMES = {
    "PYTHONHOME",
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "HERMES_HOME",
    "HERMES_DESKTOP_HERMES_ROOT",
    "HERMES_PYTHON",
    "UV_PYTHON",
    "UV_PROJECT_ENVIRONMENT",
    "BOLT_MODEL_PROXY_URL",
    "BOLT_RUNTIME_TOKEN",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--catalog-output", type=Path, default=DEFAULT_CATALOG_OUTPUT)
    parser.add_argument("--uv", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    build_root = args.build_root.resolve()
    python = args.python.resolve()
    uv = _resolve_uv(args.uv)

    _require_pinned_source(source)
    _require_python(python)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    if build_root.exists():
        raise SystemExit(f"refusing to overwrite existing build root: {build_root}")

    environment = _scrubbed_environment(build_root)
    _run([str(uv), "lock", "--check"], cwd=source, env=environment)
    staging = build_root / "source"
    _copy_staging_source(source, staging)
    overlay = _apply_bolt_overlay(staging)
    wheel_dir = build_root / "wheel"
    wheel_dir.mkdir(parents=True)
    _run(
        [str(uv), "build", "--wheel", "--clear", "--python", str(python), "--out-dir", str(wheel_dir)],
        cwd=staging,
        env=environment,
    )
    wheel = _single_wheel(wheel_dir)

    output.mkdir(parents=True)
    prefix = output / "bin"
    shutil.copytree(python.parent, prefix)
    _prune_python_distribution(prefix)
    hermes_python = prefix / "python.exe"
    hermes_acp = prefix / "hermes-acp.exe"
    shutil.copy2(hermes_python, hermes_acp)

    requirements = build_root / "requirements-acp.txt"
    _run(
        [
            str(uv), "export", "--locked", "--format", "requirements-txt", "--extra", "acp",
            "--no-emit-project", "--output-file", str(requirements),
        ],
        cwd=staging,
        env=environment,
    )
    _run(
        [
            str(uv), "pip", "install", "--break-system-packages", "--python", str(hermes_python),
            "--require-hashes", "-r", str(requirements),
        ],
        cwd=build_root,
        env=environment,
    )
    _run(
        [
            str(uv), "pip", "install", "--break-system-packages", "--python", str(hermes_python),
            "--no-deps", "--no-editable", str(wheel),
        ],
        cwd=build_root,
        env=environment,
    )

    hermes_direct_url = (
        output / "bin" / "Lib" / "site-packages" / "hermes_agent-0.18.2.dist-info" / "direct_url.json"
    )
    if _direct_url_references_source(hermes_direct_url, source):
        raise RuntimeError("Hermes wheel installation references the upstream source")
    _remove_direct_url_metadata(output / "bin" / "Lib" / "site-packages")

    licenses = output / "licenses"
    licenses.mkdir()
    shutil.copy2(source / "LICENSE", licenses / "HERMES-AGENT-MIT.txt")
    _copy_optional_notice(source, licenses, "plugins/security-guidance/LICENSE", "SECURITY-GUIDANCE-APACHE-2.0.txt")
    _copy_optional_notice(source, licenses, "plugins/security-guidance/NOTICE", "SECURITY-GUIDANCE-NOTICE.txt")
    _copy_optional_notice(source, licenses, "plugins/hermes-achievements/LICENSE", "HERMES-ACHIEVEMENTS-MIT.txt")

    _verify_portable_runtime(output, hermes_python, hermes_acp, source, environment)
    inventory_hash = _write_metadata(
        output, source, wheel, staging, overlay, python, environment, args.catalog_output.resolve(),
    )
    print(json.dumps({"output": str(output), "inventory_sha256": inventory_hash}, indent=2))
    return 0


def _require_pinned_source(source: Path) -> None:
    if not (source / "pyproject.toml").is_file() or not (source / "uv.lock").is_file():
        raise SystemExit("source must be the pinned Hermes worktree")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0 or result.stdout.strip() != UPSTREAM_COMMIT:
        raise SystemExit("source does not match the fixed Hermes commit")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=source, text=True, capture_output=True, check=False,
    )
    if status.returncode != 0 or status.stdout:
        raise SystemExit("source worktree must be clean")


def _require_python(python: Path) -> None:
    if not python.is_file():
        raise SystemExit("fixed CPython executable is unavailable")
    result = subprocess.run(
        [str(python), "-I", "-c", "import platform, sys; print(platform.architecture()[0]); print(sys.version_info[:2])"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or "64bit" not in result.stdout or "(3, 11)" not in result.stdout:
        raise SystemExit("fixed CPython must be x64 CPython 3.11")


def _resolve_uv(value: Path | None) -> Path:
    candidates = [
        value,
        Path(r"C:\Users\bi240\AppData\Local\Programs\Python\Python313\Scripts\uv.exe"),
        Path(shutil.which("uv") or ""),
    ]
    for candidate in candidates:
        if candidate is not None and str(candidate) and candidate.is_file():
            return candidate.resolve()
    raise SystemExit("uv executable is unavailable")


def _scrubbed_environment(build_root: Path) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in _SCRUBBED_ENV_NAMES
        and not any(part in name.upper() for part in _SENSITIVE_ENV_PARTS)
    }
    homes = build_root / "environment"
    env.update({
        "HOME": str(homes / "home"),
        "USERPROFILE": str(homes / "home"),
        "APPDATA": str(homes / "appdata"),
        "LOCALAPPDATA": str(homes / "localappdata"),
        "HERMES_HOME": str(homes / "hermes-home"),
        "TEMP": str(homes / "temp"),
        "TMP": str(homes / "temp"),
        "TMPDIR": str(homes / "temp"),
        "UV_CACHE_DIR": str(build_root / "uv-cache"),
        "UV_NO_CONFIG": "1",
        "PIP_CONFIG_FILE": "NUL",
    })
    for path in {Path(env["HOME"]), Path(env["HERMES_HOME"]), Path(env["TEMP"]), Path(env["UV_CACHE_DIR"])}:
        path.mkdir(parents=True, exist_ok=True)
    return env


def _copy_staging_source(source: Path, staging: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        relative = Path(directory).resolve().relative_to(source)
        if relative == Path("."):
            return {name for name in names if name in _EXCLUDED_SOURCE_DIRS or name in {".git", "dist", "build"}}
        return {name for name in names if name in {"__pycache__", ".pytest_cache", "build", "dist"}}

    shutil.copytree(source, staging, ignore=ignore)


def _apply_bolt_overlay(staging: Path) -> list[dict[str, str]]:
    changes = []
    setup = staging / "setup.py"
    original = setup.read_text(encoding="utf-8")
    updated = original.replace('        *_data_file_tree("skills"),\n', "").replace(
        '        *_data_file_tree("optional-skills"),\n', "",
    )
    changes.append(_replace_file(
        setup, original, updated, "setup.py",
        "exclude bundled skills from headless ACP runtime",
    ))

    manifest = staging / "MANIFEST.in"
    original = manifest.read_text(encoding="utf-8")
    updated = original.replace("graft skills\n", "").replace("graft optional-skills\n", "")
    changes.append(_replace_file(
        manifest, original, updated, "MANIFEST.in",
        "exclude skills from source distribution metadata",
    ))

    config = staging / "hermes_cli" / "config.py"
    original = config.read_text(encoding="utf-8")
    old = """    merged = dict(client_kwargs.get(\"default_headers\") or {})\n    merged.update(extra_headers)\n    client_kwargs[\"default_headers\"] = merged\n"""
    new = """    merged = dict(client_kwargs.get(\"default_headers\") or {})\n    suppress_authorization = any(\n        key.casefold() == \"authorization\" and value == \"\"\n        for key, value in extra_headers.items()\n    )\n    for key, value in extra_headers.items():\n        if key.casefold() != \"authorization\":\n            merged[key] = value\n    if suppress_authorization:\n        merged.pop(\"Authorization\", None)\n        merged.pop(\"authorization\", None)\n        client_kwargs[\"api_key\"] = \"\"\n    client_kwargs[\"default_headers\"] = merged\n"""
    if old not in original:
        raise RuntimeError("upstream custom-provider header hook changed")
    changes.append(_replace_file(
        config, original, original.replace(old, new), "hermes_cli/config.py",
        "empty custom Authorization suppresses OpenAI SDK bearer auth for Bolt loopback proxy",
    ))

    overlay_source = Path(__file__).with_name("hermes_acp_overlay") / "bolt_model_client.py"
    changes.append(_copy_overlay_file(
        overlay_source, staging / "acp_adapter" / "bolt_model_client.py",
        "acp_adapter/bolt_model_client.py",
        "route managed Hermes model calls through the parent ACP connection",
    ))

    session = staging / "acp_adapter" / "session.py"
    original = session.read_text(encoding="utf-8")
    old = '''        try:
            runtime = resolve_runtime_provider(requested=requested_provider or config_provider)
            kwargs.update(
                {
                    "provider": runtime.get("provider"),
                    "api_mode": api_mode or runtime.get("api_mode"),
                    "base_url": base_url or runtime.get("base_url"),
                    "api_key": runtime.get("api_key"),
                    "command": runtime.get("command"),
                    "args": list(runtime.get("args") or []),
                }
            )
        except Exception:
            logger.debug("ACP session falling back to default provider resolution", exc_info=True)

        _register_task_cwd(session_id, cwd)
        agent = AIAgent(**kwargs)
'''
    new = '''        bolt_managed = config_provider == "bolt-managed"
        if bolt_managed:
            kwargs.update({
                "provider": "custom",
                "api_mode": "chat_completions",
                "base_url": "http://127.0.0.1:9/v1",
                "api_key": "bolt-managed",
            })
        else:
            try:
                runtime = resolve_runtime_provider(requested=requested_provider or config_provider)
                kwargs.update(
                    {
                        "provider": runtime.get("provider"),
                        "api_mode": api_mode or runtime.get("api_mode"),
                        "base_url": base_url or runtime.get("base_url"),
                        "api_key": runtime.get("api_key"),
                        "command": runtime.get("command"),
                        "args": list(runtime.get("args") or []),
                    }
                )
            except Exception:
                logger.debug("ACP session falling back to default provider resolution", exc_info=True)

        _register_task_cwd(session_id, cwd)
        agent = AIAgent(**kwargs)
        if bolt_managed:
            from acp_adapter.bolt_model_client import BoltModelClient

            agent.client = BoltModelClient(session_id)
            agent.provider = "bolt-acp"
            agent.base_url = "acp://bolt"
            agent.api_key = ""
            agent._client_kwargs = {}
            agent._disable_streaming = True
'''
    changes.append(_replace_file(
        session, original, original.replace(old, new), "acp_adapter/session.py",
        "bolt-managed sessions bypass runtime provider and use the ACP model client",
    ))

    server = staging / "acp_adapter" / "server.py"
    original = server.read_text(encoding="utf-8")
    old = '''from acp_adapter.auth import TERMINAL_SETUP_AUTH_METHOD_ID, build_auth_methods, detect_provider
'''
    new = '''from acp_adapter.auth import TERMINAL_SETUP_AUTH_METHOD_ID, build_auth_methods, detect_provider
from acp_adapter.bolt_model_client import bind_bolt_model_client, unbind_bolt_model_client
'''
    changes.append(_replace_file(
        server, original, original.replace(old, new), "acp_adapter/server.py",
        "bind the managed model facade to the parent ACP event loop for one prompt",
    ))
    original = server.read_text(encoding="utf-8")
    old = '''        agent = state.agent
        agent.tool_progress_callback = tool_progress_cb
'''
    new = '''        agent = state.agent
        if conn:
            bind_bolt_model_client(agent, conn, loop)
        agent.tool_progress_callback = tool_progress_cb
'''
    changes.append(_replace_file(
        server, original, original.replace(old, new), "acp_adapter/server.py",
        "bind Core-owned model authority before the executor begins the prompt",
    ))
    original = server.read_text(encoding="utf-8")
    old = '''        except Exception:
            logger.exception("Executor error for session %s", session_id)
            with state.runtime_lock:
                state.is_running = False
                state.current_prompt_text = ""
            return PromptResponse(stop_reason="end_turn")

        if result.get("messages"):
'''
    new = '''        except Exception:
            logger.exception("Executor error for session %s", session_id)
            with state.runtime_lock:
                state.is_running = False
                state.current_prompt_text = ""
            return PromptResponse(stop_reason="end_turn")
        finally:
            unbind_bolt_model_client(agent)

        if result.get("messages"):
'''
    changes.append(_replace_file(
        server, original, original.replace(old, new), "acp_adapter/server.py",
        "cancel a pending Core model RPC when the prompt ends or its transport fails",
    ))

    helpers = staging / "agent" / "chat_completion_helpers.py"
    original = helpers.read_text(encoding="utf-8")
    old = '''            elif agent.provider == "moa":
                # MoA is a virtual chat-completions provider backed by the
                # in-process MoAClient facade. Do not rebuild a request-local
                # OpenAI client from the virtual runtime metadata.
                result["response"] = agent.client.chat.completions.create(**api_kwargs)
'''
    new = '''            elif agent.provider in {"moa", "bolt-acp"}:
                # Virtual providers own their in-process chat-completions facade.
                result["response"] = agent.client.chat.completions.create(**api_kwargs)
'''
    changes.append(_replace_file(
        helpers, original, original.replace(old, new), "agent/chat_completion_helpers.py",
        "prevent the managed ACP provider from rebuilding an HTTP client",
    ))
    return changes


def _replace_file(path: Path, old: str, new: str, relative_path: str, reason: str) -> dict[str, str]:
    if old == new:
        raise RuntimeError(f"overlay did not change {path}")
    path.write_text(new, encoding="utf-8")
    return {
        "path": relative_path,
        "before_sha256": _sha256_text(old),
        "after_sha256": _sha256_text(new),
        "reason": reason,
    }


def _copy_overlay_file(source: Path, destination: Path, relative_path: str, reason: str) -> dict[str, str]:
    if not source.is_file() or destination.exists():
        raise RuntimeError(f"overlay file is unavailable: {relative_path}")
    content = source.read_text(encoding="utf-8")
    destination.write_text(content, encoding="utf-8")
    return {
        "path": relative_path,
        "before_sha256": _sha256_text(""),
        "after_sha256": _sha256_text(content),
        "reason": reason,
    }


def _single_wheel(wheel_dir: Path) -> Path:
    wheels = tuple(wheel_dir.glob("hermes_agent-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("expected exactly one Hermes wheel")
    return wheels[0]


def _copy_optional_notice(source: Path, destination: Path, relative: str, target: str) -> None:
    candidate = source / relative
    if candidate.is_file():
        shutil.copy2(candidate, destination / target)


def _prune_python_distribution(prefix: Path) -> None:
    # ACP does not use Tk or Python development headers. Excluding them avoids
    # shipping the upstream Tcl demo sources and keeps the catalog payload focused.
    for relative in ("tcl", "include", "libs"):
        shutil.rmtree(prefix / relative, ignore_errors=True)
    for cache in prefix.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)


def _verify_portable_runtime(
    output: Path, python: Path, hermes_acp: Path, source: Path, environment: dict[str, str],
) -> None:
    site_packages = output / "bin" / "Lib" / "site-packages"
    editable = tuple(site_packages.glob("__editable__*.pth"))
    hermes_direct_url = site_packages / "hermes_agent-0.18.2.dist-info" / "direct_url.json"
    if editable or _direct_url_references_source(hermes_direct_url, source):
        raise RuntimeError("portable runtime contains editable Hermes installation metadata")
    check = _run(
        [str(hermes_acp), "-I", "-B", "-m", "acp_adapter.entry", "--check"],
        cwd=output,
        env=environment,
    )
    if check.stdout.strip() != "Hermes ACP check OK":
        raise RuntimeError("portable Hermes ACP check did not succeed")
    imports = _run(
        [
            str(python), "-I", "-B", "-c",
            "import acp_adapter, hermes_cli, run_agent; print(acp_adapter.__file__); print(hermes_cli.__file__); print(run_agent.__file__)",
        ],
        cwd=output,
        env=environment,
    ).stdout.splitlines()
    root = site_packages.resolve()
    if len(imports) != 3 or any(not _within(Path(value).resolve(), root) for value in imports):
        raise RuntimeError("portable runtime imports do not resolve from payload site-packages")
    forbidden = ("E:\\HermesData", str(source), "BOLT_RUNTIME_TOKEN")
    for path in _iter_text_files(output):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if any(value in content for value in forbidden):
            raise RuntimeError(f"portable runtime leaks a forbidden build input: {path}")


def _direct_url_references_source(path: Path, source: Path) -> bool:
    if not path.is_file():
        return False
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    if metadata.get("dir_info", {}).get("editable") is True:
        return True
    return str(source).casefold().replace("\\", "/") in json.dumps(metadata).casefold().replace("\\", "/")


def _remove_direct_url_metadata(site_packages: Path) -> None:
    for path in site_packages.rglob("direct_url.json"):
        path.unlink()


def _write_metadata(
    output: Path, source: Path, wheel: Path, staging: Path, overlay: list[dict[str, str]],
    python: Path, environment: dict[str, str], catalog_output: Path,
) -> str:
    metadata = output / "metadata"
    metadata.mkdir()
    provenance = {
        "schema_version": 1,
        "runtime_id": "hermes",
        "implementation_version": VERSION,
        "upstream": {"source": SOURCE_URL, "commit": UPSTREAM_COMMIT},
        "scope": "headless_acp_only",
        "python": {"version": _python_version(python, environment), "architecture": "x64"},
        "inputs": {
            "pyproject_toml_sha256": _sha256(source / "pyproject.toml"),
            "uv_lock_sha256": _sha256(source / "uv.lock"),
            "license_sha256": _sha256(source / "LICENSE"),
            "wheel_sha256": _sha256(wheel),
        },
        "excluded_source_directories": sorted(_EXCLUDED_SOURCE_DIRS),
        "overlay": overlay,
        "launcher": {
            "executable_relative_path": "bin/hermes-acp.exe",
            "args": ["-I", "-B", "-m", "acp_adapter.entry"],
        },
        "staging_source_sha256": _tree_hash(staging),
    }
    (metadata / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    inventory = [
        {"relative_path": path.relative_to(output).as_posix(), "sha256": _sha256(path)}
        for path in sorted(output.rglob("*"))
        if path.is_file()
    ]
    _write_catalog_inventory(catalog_output, inventory)
    return hashlib.sha256(
        json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _write_catalog_inventory(path: Path, inventory: list[dict[str, str]]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite catalog inventory: {path}")
    lines = [
        '"""Generated fixed inventory for the bundled Hermes ACP release."""',
        "",
        "HERMES_RELEASE_FILES = (",
    ]
    lines.extend(
        f"    ({item['relative_path']!r}, {item['sha256']!r})," for item in inventory
    )
    lines.extend([
        ")",
        "",
        "__all__ = [\"HERMES_RELEASE_FILES\"]",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _python_version(python: Path, environment: dict[str, str]) -> str:
    result = _run(
        [str(python), "-I", "-c", "import platform; print(platform.python_version())"],
        cwd=python.parent,
        env=environment,
    )
    return result.stdout.strip()


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=True)


def _iter_text_files(root: Path) -> Iterable[Path]:
    text_suffixes = {".cfg", ".ini", ".json", ".pth", ".py", ".pyw", ".toml", ".txt", ".yaml", ".yml"}
    return (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in text_suffixes)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
