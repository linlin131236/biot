"""Tests for TestRunnerIntegration."""
from pathlib import Path

import pytest

from bolt_core.test_runner_integration import TestRunnerIntegration


class TestTestRunner:
    def test_whitelist_command_runs(self, tmp_path):
        runner = TestRunnerIntegration(project_dir=str(tmp_path))
        result = runner.run("shared_test")
        # shared_test may work or not depending on env, but should not be blocked
        assert result.status != "blocked"

    def test_non_whitelist_blocked(self, tmp_path):
        runner = TestRunnerIntegration()
        result = runner.run("rm_all_files")
        assert result.status == "blocked"
        assert "白名单" in result.summary

    def test_dangerous_args_blocked(self, tmp_path):
        runner = TestRunnerIntegration()
        result = runner.run("shared_test", extra_args=["&& rm -rf /"])
        assert result.status == "blocked"
        assert "危险" in result.summary

    def test_push_blocked_in_args(self, tmp_path):
        runner = TestRunnerIntegration()
        result = runner.run("shared_test", extra_args=["git push origin main"])
        assert result.status == "blocked"

    def test_list_available(self, tmp_path):
        runner = TestRunnerIntegration()
        info = runner.list_available()
        assert "available_tests" in info
        assert "backend_unit" in info["available_tests"]
        assert "desktop_test" in info["available_tests"]

    def test_history_records_runs(self, tmp_path):
        runner = TestRunnerIntegration(project_dir=str(tmp_path))
        runner.run("shared_test")
        assert len(runner.history()) >= 1

    def test_nonexistent_test_id_blocked(self, tmp_path):
        runner = TestRunnerIntegration()
        result = runner.run("nonexistent_test_xyz")
        assert result.status == "blocked"
