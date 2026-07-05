from bolt_core.path_guard import PathGuard


def test_allows_file_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "src" / "app.py"
    target.parent.mkdir()
    target.write_text("print('bolt')", encoding="utf-8")

    result = PathGuard(str(workspace)).check(str(target))

    assert result.allowed is True
    assert result.path == target.resolve()


def test_denies_path_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    outside.write_text("no", encoding="utf-8")

    result = PathGuard(str(workspace)).check(str(outside))

    assert result.allowed is False
    assert result.reason == "path outside workspace"


def test_denies_parent_traversal_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / ".." / "outside.txt"

    result = PathGuard(str(workspace)).check(str(target))

    assert result.allowed is False
    assert result.reason == "path outside workspace"


def test_denies_secret_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = workspace / ".env"
    secret.write_text("TOKEN=secret", encoding="utf-8")

    result = PathGuard(str(workspace)).check(str(secret))

    assert result.allowed is False
    assert result.reason == "secret path denied"


def test_denies_secret_directories(tmp_path):
    workspace = tmp_path / "workspace"
    target = workspace / ".ssh" / "id_rsa"
    target.parent.mkdir(parents=True)
    target.write_text("secret", encoding="utf-8")

    result = PathGuard(str(workspace)).check(str(target))

    assert result.allowed is False
    assert result.reason == "secret path denied"
