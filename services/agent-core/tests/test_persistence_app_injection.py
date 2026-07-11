from bolt_core.app import create_app


def test_app_creates_persistence_only_from_explicit_trusted_root(tmp_path):
    workspace = tmp_path / "workspace"
    trusted_root = tmp_path / "electron-user-data"

    app = create_app(project_dir=workspace, persistence_root=trusted_root)

    assert app.state.persistence is not None
    assert app.state.persistence.database.path == trusted_root / "state" / "bolt.sqlite3"
    assert not (workspace / ".bolt" / "bolt.sqlite3").exists()


def test_app_without_trusted_root_does_not_create_a_workspace_database(tmp_path):
    workspace = tmp_path / "workspace"

    app = create_app(project_dir=workspace)

    assert app.state.persistence is None
    assert not (workspace / ".bolt" / "bolt.sqlite3").exists()
