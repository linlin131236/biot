from bolt_core.tool_schemas import all_tool_schemas, tool_schema


def test_all_tool_schemas_returns_four_tools():
    schemas = all_tool_schemas()
    names = [s["function"]["name"] for s in schemas]
    assert "file.read" in names
    assert "files.search" in names
    assert "file.write" in names
    assert "shell.execute" in names


def test_each_schema_has_required_fields():
    for schema in all_tool_schemas():
        assert schema["type"] == "function"
        func = schema["function"]
        assert isinstance(func["name"], str)
        assert isinstance(func["description"], str)
        assert "parameters" in func
        params = func["parameters"]
        assert params["type"] == "object"
        assert "properties" in params


def test_tool_schema_by_name():
    schema = tool_schema("file.read")
    assert schema is not None
    assert schema["function"]["name"] == "file.read"


def test_tool_schema_unknown_returns_none():
    assert tool_schema("unknown.tool") is None


def test_file_write_requires_path_and_content():
    schema = tool_schema("file.write")
    required = schema["function"]["parameters"]["required"]
    assert "path" in required
    assert "proposed_content" in required


def test_shell_execute_requires_command():
    schema = tool_schema("shell.execute")
    required = schema["function"]["parameters"]["required"]
    assert "command" in required
