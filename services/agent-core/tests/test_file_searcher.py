from bolt_core.file_searcher import search_workspace_files


def test_finds_file_by_name(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "app.py").write_text("print('a')", encoding="utf-8")
    (workspace / "src" / "other.ts").write_text("export const x = 1", encoding="utf-8")

    outcome = search_workspace_files(str(workspace), "app.py", mode="name")

    assert outcome.status == "executed"
    paths = [hit.path for hit in outcome.hits]
    assert any(p.endswith("app.py") for p in paths)
    assert not any(p.endswith("other.ts") for p in paths)


def test_excludes_node_modules_and_dist(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "node_modules" / "pkg").mkdir(parents=True)
    (workspace / "node_modules" / "pkg" / "target.py").write_text("x", encoding="utf-8")
    (workspace / "dist").mkdir()
    (workspace / "dist" / "target.py").write_text("x", encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "target.py").write_text("x", encoding="utf-8")

    outcome = search_workspace_files(str(workspace), "target.py", mode="name")

    paths = [hit.path for hit in outcome.hits]
    assert len(paths) == 1
    assert "src" in paths[0].replace("\\", "/")


def test_content_mode_matches_lines(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text("hello bolt\nsecond line\nBOLT again", encoding="utf-8")

    outcome = search_workspace_files(str(workspace), "bolt", mode="content")

    assert outcome.status == "executed"
    assert len(outcome.hits) == 2
    assert outcome.hits[0].line == 1
    assert "bolt" in outcome.hits[0].snippet.lower()


def test_content_mode_skips_secret_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".env").write_text("TOKEN=bolt-secret", encoding="utf-8")

    outcome = search_workspace_files(str(workspace), "bolt", mode="content")

    assert outcome.status == "executed"
    assert outcome.hits == []


def test_both_mode_matches_names_and_contents(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "bolt_file.py").write_text("nothing", encoding="utf-8")
    (workspace / "notes.md").write_text("contains bolt token", encoding="utf-8")

    outcome = search_workspace_files(str(workspace), "bolt", mode="both")

    assert outcome.status == "executed"
    snippets = [hit.snippet for hit in outcome.hits]
    assert "bolt_file.py" in snippets
    assert "contains bolt token" in snippets


def test_empty_query_returns_failed(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outcome = search_workspace_files(str(workspace), "", mode="name")

    assert outcome.status == "failed"
    assert outcome.error == "empty query"
