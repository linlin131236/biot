from bolt_core.file_indexer import index_workspace_files
from bolt_core.intent_router import classify_intent
from bolt_core.workspace_scanner import scan_workspace


def test_scanner_detects_package_manager_languages_and_entries(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "package.json").write_text('{"scripts":{"test":"vitest","build":"tsc"}}', encoding="utf-8")
    (workspace / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'", encoding="utf-8")
    (workspace / "src" / "main.ts").write_text("export const main = true", encoding="utf-8")

    profile = scan_workspace(str(workspace))

    assert profile.package_manager == "pnpm"
    assert "typescript" in profile.languages
    assert any(path.endswith("package.json") for path in profile.manifests)
    assert any(path.endswith("src/main.ts") for path in profile.entry_files)
    assert "pnpm test" in profile.test_commands
    assert "pnpm build" in profile.build_commands


def test_scanner_excludes_generated_and_secret_paths(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "node_modules" / "pkg").mkdir(parents=True)
    (workspace / ".git").mkdir(parents=True)
    (workspace / "dist").mkdir(parents=True)
    (workspace / ".venv").mkdir(parents=True)
    (workspace / "src").mkdir(parents=True)
    (workspace / "node_modules" / "pkg" / "package.json").write_text("{}", encoding="utf-8")
    (workspace / ".env").write_text("TOKEN=secret", encoding="utf-8")
    (workspace / "src" / "app.py").write_text("print('ok')", encoding="utf-8")

    profile = scan_workspace(str(workspace))

    paths = "\n".join(profile.manifests + profile.entry_files)
    assert "node_modules" not in paths
    assert ".git" not in paths
    assert "dist" not in paths
    assert ".venv" not in paths
    assert ".env" not in paths
    assert "python" in profile.languages


def test_indexer_extracts_imports_exports_and_symbols(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "app.ts").write_text(
        "import { x } from './x';\nexport function run() {}\nexport const value = 1;\nclass Local {}",
        encoding="utf-8",
    )
    (workspace / "src" / "main.py").write_text("from os import path\nclass Service:\n    pass\ndef build():\n    pass\n", encoding="utf-8")

    index = index_workspace_files(str(workspace))

    entries = {entry.path.replace("\\", "/"): entry for entry in index.entries}
    ts_entry = next(entry for path, entry in entries.items() if path.endswith("src/app.ts"))
    py_entry = next(entry for path, entry in entries.items() if path.endswith("src/main.py"))
    assert "./x" in ts_entry.imports
    assert "run" in ts_entry.exports
    assert "value" in ts_entry.exports
    assert "Local" in ts_entry.symbols
    assert "os" in py_entry.imports
    assert "Service" in py_entry.symbols
    assert "build" in py_entry.symbols


def test_indexer_limits_and_skips_secret_paths(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("SECRET=1", encoding="utf-8")
    for index in range(5):
        (workspace / f"file_{index}.py").write_text(f"def f{index}():\n    pass\n", encoding="utf-8")

    result = index_workspace_files(str(workspace), max_files=2, max_entries=2)

    indexed_paths = "\n".join(entry.path for entry in result.entries)
    assert result.truncated is True
    assert len(result.entries) == 2
    assert ".env" not in indexed_paths
    assert result.skipped["secret_path"] >= 1


def test_intent_router_classifies_common_requests():
    assert classify_intent("请修复这个 bug").category == "debug"
    assert classify_intent("优化这个页面 UI").category == "ui_improvement"
    assert classify_intent("运行 pnpm test").category == "run_command"
    assert classify_intent("review this change").category == "review"
    assert classify_intent("解释一下架构").category == "question"
