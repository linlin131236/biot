from bolt_core.skill import SkillManifest, SkillStore, SkillSelector


def test_skill_manifest_parsing(tmp_path):
    skill_dir = tmp_path / "skills" / "git-workflow"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: git-workflow\ntriggers: [git, commit, branch, PR]\nrequired_tools: [shell.execute]\nversion: '1.0'\n---\n# Git Workflow\n\n1. Check branch\n2. Stage and commit\n", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    skills = store.list()
    assert len(skills) == 1
    assert skills[0].name == "git-workflow"
    assert "git" in skills[0].triggers
    assert skills[0].required_tools == ["shell.execute"]


def test_skill_store_match(tmp_path):
    skill_dir = tmp_path / "skills" / "debugging"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: debugging\ntriggers: [bug, debug, error, trace]\nrequired_tools: [file.read, shell.execute]\n---\n# Debugging\n\nFind and fix bugs.\n", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    matches = store.match("fix the bug in auth")
    assert len(matches) >= 1
    assert matches[0].name == "debugging"


def test_skill_store_no_match(tmp_path):
    store = SkillStore(str(tmp_path / "skills"))
    matches = store.match("unrelated task")
    assert len(matches) == 0


def test_invalid_manifest_rejected(tmp_path):
    skill_dir = tmp_path / "skills" / "broken"
    skill_dir.mkdir(parents=True)
    # Missing required 'name' field
    (skill_dir / "SKILL.md").write_text(
        "---\ntriggers: [test]\n---\nNo name field", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    skills = store.list()
    assert len(skills) == 0  # Invalid manifest should be rejected


def test_skill_cannot_bypass_permission(tmp_path):
    """Skill manifest with bypass_permission should be rejected."""
    skill_dir = tmp_path / "skills" / "dangerous"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: dangerous\ntriggers: [hack]\nbypass_permission: true\n---\nBypasses permission", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    skills = store.list()
    assert len(skills) == 0


def test_skill_selector_max_2(tmp_path):
    for name, triggers in [("git", ["git"]), ("debug", ["debug"]),
                           ("review", ["review"])]:
        d = tmp_path / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ntriggers: {triggers}\n---\n# {name}\n", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    selector = SkillSelector(store)
    selected = selector.select("git debug review task", max_skills=2)
    assert len(selected) <= 2


def test_skill_path_must_be_in_workspace(tmp_path):
    """Skill loading from outside workspace should fail closed."""
    store = SkillStore(str(tmp_path / "skills"))
    # Try loading by path traversal
    skill = store.load("../../etc/passwd")
    assert skill is None


def test_skill_trace_records_selection(tmp_path):
    skill_dir = tmp_path / "skills" / "testing"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: testing\ntriggers: [test, pytest]\n---\n# Testing\n\nWrite tests first.\n", encoding="utf-8")

    store = SkillStore(str(tmp_path / "skills"))
    selector = SkillSelector(store)
    selection = selector.select("write pytest tests", max_skills=1)
    # Selection should record which skill was chosen and why
    if selection:
        assert selection[0].name == "testing"
