from bolt_core.evidence import Evidence, EvidenceLog


def test_evidence_is_immutable():
    entry = Evidence(step=1, action="file.read", result="executed", output="hello", files_changed=[])
    assert entry.step == 1
    assert entry.action == "file.read"


def test_evidence_log_records_steps():
    log = EvidenceLog()
    log.record(step=1, action="file.read", result="executed", output="content", files_changed=[])
    log.record(step=2, action="shell.execute", result="executed", output="Python 3.11", files_changed=[])

    assert len(log.entries) == 2
    assert log.entries[0].step == 1
    assert log.entries[1].step == 2


def test_evidence_log_summary_for_context():
    log = EvidenceLog()
    for i in range(5):
        log.record(step=i + 1, action="file.read", result="executed", output=f"output_{i}", files_changed=[])

    summary = log.recent_summary(max_entries=3)

    assert len(summary) == 3
    assert summary[0].step == 3
    assert summary[2].step == 5


def test_evidence_log_empty_summary():
    log = EvidenceLog()
    summary = log.recent_summary(max_entries=5)
    assert summary == []


def test_evidence_log_files_changed_tracked():
    log = EvidenceLog()
    log.record(step=1, action="file.patch", result="executed", output="applied", files_changed=["src/app.py", "tests/test_app.py"])

    assert log.entries[0].files_changed == ["src/app.py", "tests/test_app.py"]


def test_evidence_has_timestamp():
    log = EvidenceLog()
    log.record(step=1, action="file.read", result="executed", output="content", files_changed=[])

    assert log.entries[0].timestamp is not None
    assert len(log.entries[0].timestamp) > 0
