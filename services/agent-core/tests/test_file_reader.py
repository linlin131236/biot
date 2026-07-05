from bolt_core.file_reader import read_workspace_file


def test_reads_text_file_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.py"
    target.write_text("print('bolt')", encoding="utf-8")

    outcome = read_workspace_file(str(target), str(workspace))

    assert outcome.status == "executed"
    assert outcome.content == "print('bolt')"
    assert outcome.error is None


def test_denies_path_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.txt"
    workspace.mkdir()
    outside.write_text("no", encoding="utf-8")

    outcome = read_workspace_file(str(outside), str(workspace))

    assert outcome.status == "failed"
    assert outcome.error == "path outside workspace"
    assert outcome.content is None


def test_denies_secret_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = workspace / ".env"
    secret.write_text("TOKEN=secret", encoding="utf-8")

    outcome = read_workspace_file(str(secret), str(workspace))

    assert outcome.status == "failed"
    assert outcome.error == "secret path denied"


def test_reports_missing_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    missing = workspace / "ghost.py"

    outcome = read_workspace_file(str(missing), str(workspace))

    assert outcome.status == "failed"
    assert outcome.error == "file not found"


def test_rejects_binary_file(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    binary = workspace / "blob.bin"
    binary.write_bytes(b"\x00\x01\xff\xfe")

    outcome = read_workspace_file(str(binary), str(workspace))

    assert outcome.status == "failed"
    assert outcome.error == "binary file not readable"


def test_rejects_file_over_read_limit(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    big = workspace / "big.txt"
    big.write_bytes(b"x" * (300 * 1024))

    outcome = read_workspace_file(str(big), str(workspace))

    assert outcome.status == "failed"
    assert outcome.error == "file exceeds read limit"
