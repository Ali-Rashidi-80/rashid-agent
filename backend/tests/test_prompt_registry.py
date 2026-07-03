"""Prompt registry tests."""

from app.services.prompt_registry import PromptRegistry


def test_load_manifest():
    reg = PromptRegistry()
    manifest = reg.load_manifest()
    assert "version" in manifest or manifest == {} or "default_mode" in manifest


def test_load_persona_not_empty():
    reg = PromptRegistry()
    persona = reg.load_persona()
    assert len(persona) > 10


def test_load_modes():
    reg = PromptRegistry()
    assert "تحلیل" in reg.load_mode("ask") or len(reg.load_mode("ask")) > 0
    assert len(reg.load_mode("agent")) > 0


def test_load_schema():
    reg = PromptRegistry()
    schema = reg.load_edits_schema()
    assert "start_number_line" in schema


def test_negative_constraints():
    reg = PromptRegistry()
    nc = reg.load_negative_constraints()
    assert "هرگز" in nc
