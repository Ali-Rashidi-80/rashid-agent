"""Pip safe execution tests."""

from app.services.pip_safe import run_pip_safe


def test_pip_list_allowed():
    result = run_pip_safe(["list", "--format=freeze"])
    assert "ok" in result


def test_pip_rm_rejected():
    result = run_pip_safe(["rm", "-rf", "/"])
    assert result["ok"] is False
