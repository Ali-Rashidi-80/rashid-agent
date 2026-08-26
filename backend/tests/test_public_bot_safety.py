"""DoD: public bot / messenger paths never enable agent edits or project FS."""

from __future__ import annotations

import ast
import inspect

from app.routers import public_bots
from app.services import telegram_webhook


def test_public_bot_chat_forces_ask_rag_only():
    source = inspect.getsource(public_bots.public_bot_chat_stream)
    assert 'mode="ask"' in source
    assert "rag_only=True" in source
    # Must not switch into agent/plan modes from request body.
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "generate_stream":
            kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            mode = kwargs.get("mode")
            assert isinstance(mode, ast.Constant) and mode.value == "ask"
            rag = kwargs.get("rag_only")
            assert isinstance(rag, ast.Constant) and rag.value is True


def test_telegram_webhook_ask_helper_is_rag_only():
    source = inspect.getsource(telegram_webhook)
    assert "rag_only=True" in source or "rag_only = True" in source
    assert 'mode="ask"' in source or "mode='ask'" in source
    # Hard guard: webhook module must not import edits/pip routers.
    assert "app.routers.edits" not in source
    assert "app.routers.pip" not in source
