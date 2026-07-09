from bolt_core.gate_freeze_service import GateFrozenError, GateFreezeService


def test_initial_state_not_frozen():
    service = GateFreezeService()
    service.unfreeze()
    assert service.is_frozen() is False


def test_freeze_blocks_gate():
    service = GateFreezeService()
    result = service.freeze(reason="生产冻结")
    assert result["frozen"] is True
    assert result["reason"] == "生产冻结"
    assert service.is_frozen() is True
    try:
        service.assert_not_frozen()
    except GateFrozenError as exc:
        assert "生产冻结" in str(exc)
    else:
        raise AssertionError("frozen gate should reject gated operations")


def test_unfreeze_returns_to_normal():
    service = GateFreezeService()
    service.freeze(reason="维护")
    result = service.unfreeze()
    assert result["frozen"] is False
    assert service.is_frozen() is False


def test_freeze_tracks_count():
    service = GateFreezeService()
    service.unfreeze()
    before = service.get_status()["freeze_count"]
    service.freeze()
    service.unfreeze()
    service.freeze()
    assert service.get_status()["freeze_count"] == before + 2


def test_status_returns_reason_when_frozen():
    service = GateFreezeService()
    service.freeze(reason="紧急冻结")
    status = service.get_status()
    assert status["frozen"] is True
    assert status["reason"] == "紧急冻结"


def test_status_returns_empty_reason_when_not_frozen():
    service = GateFreezeService()
    service.unfreeze()
    status = service.get_status()
    assert status["frozen"] is False
    assert status["reason"] == ""
