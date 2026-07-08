"""Tests for SleepWakeEngine."""
import pytest

from bolt_core.sleep_wake_engine import SleepWakeEngine, SleepState


def test_initial_state_is_awake():
    engine = SleepWakeEngine()
    assert engine.get_status()["state"] == "awake"


def test_sleep_enters_sleeping_state():
    engine = SleepWakeEngine()
    result = engine.sleep(duration_seconds=30, reason="测试待机")
    assert result["state"] == "sleeping"
    assert result["duration_seconds"] == 30
    assert "测试待机" in result["reason"]


def test_wake_returns_to_awake():
    engine = SleepWakeEngine()
    engine.sleep(duration_seconds=30)
    result = engine.wake(trigger="测试唤醒")
    assert result["state"] == "awake"
    assert result["trigger"] == "测试唤醒"


def test_wake_when_already_awake_returns_message():
    engine = SleepWakeEngine()
    result = engine.wake(trigger="test")
    assert result["state"] == "awake"
    assert "无需唤醒" in result["message"]


def test_get_status_returns_history():
    engine = SleepWakeEngine()
    engine.sleep(duration_seconds=10)
    engine.wake(trigger="test")
    status = engine.get_status()
    assert status["history_count"] == 2
    assert len(status["history"]) == 2


def test_sleep_wake_cycle():
    engine = SleepWakeEngine()
    # Sleep
    sleep_result = engine.sleep(duration_seconds=5)
    assert sleep_result["state"] == "sleeping"
    # Wake
    wake_result = engine.wake(trigger="auto")
    assert wake_result["state"] == "awake"
    # Status
    status = engine.get_status()
    assert status["is_sleeping"] is False
