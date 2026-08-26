"""Unit checks for Telegram professional copy helpers."""

from app.services.telegram_bot_profile import (
    BOT_COMMANDS,
    BOT_DESCRIPTION,
    BOT_SHORT_DESCRIPTION,
    BTN_SHARE_PHONE,
    guest_reply_keyboard,
    help_message,
    is_meta_question,
    welcome_message,
)


def test_profile_copy_is_persian_and_bounded():
    assert "عدل امید" in BOT_SHORT_DESCRIPTION
    assert len(BOT_SHORT_DESCRIPTION) <= 120
    assert len(BOT_DESCRIPTION) <= 512
    assert {c["command"] for c in BOT_COMMANDS} >= {"start", "login", "help", "status", "logout"}


def test_welcome_and_guest_keyboard():
    text = welcome_message("دستیار دانش")
    assert "دستیار دانش" in text
    assert BTN_SHARE_PHONE in text
    kb = guest_reply_keyboard()["keyboard"]
    flat = []
    for row in kb:
        for btn in row:
            flat.append(btn.get("text"))
            if btn.get("request_contact"):
                assert btn["text"] == BTN_SHARE_PHONE
    assert BTN_SHARE_PHONE in flat
    assert is_meta_question("What can this bot do?")
    assert "پایگاه دانش" in help_message()
