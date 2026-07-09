from pathlib import Path


def resolve_app_workspace(project_dir: str | Path | None, env_workspace: str | None, lock_default: bool = False) -> tuple[Path, str | None]:
    explicit_workspace = project_dir or env_workspace
    workspace_root = Path(explicit_workspace or Path.cwd()).resolve()
    if explicit_workspace or lock_default:
        return workspace_root, str(workspace_root)
    return workspace_root, None


def resolve_run_workspace(workspace: str | None, default_workspace: str, locked_workspace: str | None) -> str:
    resolved = Path(workspace or default_workspace).resolve()
    if locked_workspace:
        try:
            resolved.relative_to(Path(locked_workspace))
        except ValueError as exc:
            raise ValueError("workspace outside locked root") from exc
    return str(resolved)
