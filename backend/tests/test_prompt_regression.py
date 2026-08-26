"""Prompt regression golden cases."""

import pytest

from app.services.prompt_registry import PromptRegistry


@pytest.mark.parametrize("mode", ["ask", "plan", "agent"])
def test_mode_files_exist(mode):
    reg = PromptRegistry()
    text = reg.load_mode(mode)
    assert len(text) > 5


@pytest.mark.parametrize("i", range(12))
def test_manifest_stable(i):
    reg = PromptRegistry()
    m = reg.load_manifest()
    assert m.get("version") == "1.0.0" or "default_mode" in m
