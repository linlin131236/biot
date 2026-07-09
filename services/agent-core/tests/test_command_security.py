from bolt_core.command_security import parse_command_argv


def test_parse_command_argv_accepts_simple_argv_command():
    parsed, error = parse_command_argv("python --version")

    assert error is None
    assert parsed is not None
    assert parsed.argv == ["python", "--version"]


def test_parse_command_argv_rewrites_echo_without_shell():
    parsed, error = parse_command_argv("echo hello")

    assert error is None
    assert parsed is not None
    assert parsed.argv[1:3] == ["-c", "import sys; print(' '.join(sys.argv[1:]))"]
    assert parsed.argv[-1] == "hello"


def test_parse_command_argv_rejects_shell_control_operators():
    for command, marker in [
        ("python --version && whoami", "&"),
        ("python --version; whoami", ";"),
        ("cat README.md | powershell", "|"),
        ("python --version > out.txt", ">"),
        ("python --version < in.txt", "<"),
        ("echo `whoami`", "`"),
        ("echo $(whoami)", "$("),
        ("python --version\nwhoami", "\n"),
    ]:
        parsed, error = parse_command_argv(command)

        assert parsed is None
        assert error == f"shell control syntax not allowed: {marker}"


def test_parse_command_argv_allows_quoted_control_characters_as_literals():
    parsed, error = parse_command_argv("python -c \"print('a|b;c')\"")

    assert error is None
    assert parsed is not None
    assert parsed.argv == ["python", "-c", "print('a|b;c')"]


def test_parse_command_argv_rejects_unclosed_quotes():
    parsed, error = parse_command_argv("python -c \"print(1)")

    assert parsed is None
    assert error is not None
    assert error.startswith("invalid command syntax:")
