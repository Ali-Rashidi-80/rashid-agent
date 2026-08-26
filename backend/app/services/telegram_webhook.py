"""Handle Telegram updates for an org-bot-linked integration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.models.messenger import MessengerIntegration, MessengerLink, ProcessedMessengerUpdate
from app.db.models.org_bot import OrgBot
from app.db.repositories.org_bot import OrgBotRepository
from app.domain.sse_events import parse_sse_chunks
from app.services.generate_stream import generate_stream
from app.services.phone_normalize import normalize_otp_code, normalize_phone_for_storage
from app.services.phone_otp import request_phone_otp
from app.services.project_path import ProjectPathService
from app.services.secrets_crypto import decrypt_secret
from app.services.telegram_api import answer_callback_query, get_me, send_message
from app.services.telegram_bot_profile import (
    BTN_ADMIN_CODE,
    BTN_ASK,
    BTN_HELP,
    BTN_LOGOUT,
    BTN_RESEND,
    BTN_SHARE_PHONE,
    BTN_STATUS,
    admin_code_prompt,
    ask_prompt_message,
    authed_reply_keyboard,
    await_otp_reply_keyboard,
    contact_rejected_message,
    guest_inline_keyboard,
    guest_reply_keyboard,
    help_message,
    inactive_bot_message,
    is_meta_question,
    login_failed_message,
    login_success_message,
    logout_message,
    meta_capabilities_message,
    otp_failed_message,
    otp_sent_message,
    status_message,
    unauthorized_message,
    welcome_message,
)
from app.services.telegram_session import (
    STATE_AUTHED,
    STATE_AWAIT_ADMIN,
    STATE_AWAIT_OTP,
    STATE_GUEST,
    clear_state,
    get_state,
    set_state,
)

logger = structlog.get_logger()


async def mark_processed(db: AsyncSession, integration_id: uuid.UUID, update_id: int) -> bool:
    existing = await db.execute(
        select(ProcessedMessengerUpdate).where(
            ProcessedMessengerUpdate.integration_id == integration_id,
            ProcessedMessengerUpdate.update_id == update_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False
    db.add(
        ProcessedMessengerUpdate(
            id=uuid.uuid4(),
            integration_id=integration_id,
            update_id=update_id,
        )
    )
    try:
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False


async def is_chat_authorized(db: AsyncSession, integration_id: uuid.UUID, chat_id: str) -> bool:
    result = await db.execute(
        select(MessengerLink).where(
            MessengerLink.integration_id == integration_id,
            MessengerLink.chat_id == chat_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def authorize_chat(
    db: AsyncSession,
    *,
    integration: MessengerIntegration,
    chat_id: str,
) -> None:
    if await is_chat_authorized(db, integration.id, chat_id):
        return
    db.add(
        MessengerLink(
            id=uuid.uuid4(),
            integration_id=integration.id,
            tenant_id=integration.tenant_id,
            chat_id=chat_id,
            authorized_at=datetime.now(UTC),
        )
    )
    await db.commit()


async def deauthorize_chat(db: AsyncSession, *, integration_id: uuid.UUID, chat_id: str) -> None:
    await db.execute(
        delete(MessengerLink).where(
            MessengerLink.integration_id == integration_id,
            MessengerLink.chat_id == chat_id,
        )
    )
    await db.commit()


def _normalize_command(text: str) -> str:
    first = (text or "").strip().split(maxsplit=1)[0]
    if "@" in first:
        first = first.split("@", 1)[0]
    return first.lower()


async def _resolve_username(
    *,
    api_base: str,
    token: str,
    integration: MessengerIntegration,
) -> str | None:
    if integration.external_username:
        return integration.external_username.lstrip("@")
    me = await get_me(api_base=api_base, bot_token=token)
    username = me.get("username")
    return str(username) if username else None


async def _send_welcome(
    *,
    api_base: str,
    token: str,
    chat_id: str,
    bot_title: str,
    bot_username: str | None,
) -> None:
    await send_message(
        api_base=api_base,
        bot_token=token,
        chat_id=chat_id,
        text=welcome_message(bot_title),
        reply_markup=guest_reply_keyboard(),
    )
    await send_message(
        api_base=api_base,
        bot_token=token,
        chat_id=chat_id,
        text="میانبرها:",
        reply_markup=guest_inline_keyboard(bot_username),
    )


async def _handle_phone_share(
    *,
    db: AsyncSession,
    settings: Settings,
    integration: MessengerIntegration,
    bot: OrgBot,
    api_base: str,
    token: str,
    chat_id: str,
    phone_raw: str,
) -> None:
    result = await request_phone_otp(
        db,
        settings,
        bot,
        phone_raw=phone_raw,
        rate_key_extra=chat_id,
    )
    phone = normalize_phone_for_storage(phone_raw) or ""
    if not result.accepted and result.error == "rate_limited":
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text="لطفاً کمی صبر کنید و دوباره تلاش کنید.",
            reply_markup=guest_reply_keyboard(),
        )
        return
    if result.sent:
        await set_state(str(integration.id), chat_id, state=STATE_AWAIT_OTP, phone=phone or None)
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=otp_sent_message(),
            reply_markup=await_otp_reply_keyboard(),
        )
        return
    if result.error and result.error not in (None, "rate_limited"):
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=otp_failed_message(),
            reply_markup=guest_reply_keyboard(),
        )
        return
    # Neutral (not allowlisted or invalid) — same copy, stay guest
    await set_state(str(integration.id), chat_id, state=STATE_AWAIT_OTP, phone=phone or None)
    await send_message(
        api_base=api_base,
        bot_token=token,
        chat_id=chat_id,
        text=otp_sent_message(),
        reply_markup=await_otp_reply_keyboard(),
    )


async def _try_login_code(
    *,
    db: AsyncSession,
    integration: MessengerIntegration,
    bot: OrgBot,
    bot_repo: OrgBotRepository,
    api_base: str,
    token: str,
    chat_id: str,
    code: str,
) -> bool:
    login = await bot_repo.login(bot, secret=code)
    if login is None:
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=login_failed_message(),
            reply_markup=await_otp_reply_keyboard(),
        )
        return False
    await authorize_chat(db, integration=integration, chat_id=chat_id)
    await set_state(str(integration.id), chat_id, state=STATE_AUTHED)
    await send_message(
        api_base=api_base,
        bot_token=token,
        chat_id=chat_id,
        text=login_success_message(),
        reply_markup=authed_reply_keyboard(),
    )
    return True


async def _answer_rag(
    *,
    db: AsyncSession,
    settings: Settings,
    bot: OrgBot,
    bot_repo: OrgBotRepository,
    api_base: str,
    token: str,
    chat_id: str,
    text: str,
    update_id: int,
) -> None:
    project = ProjectPathService(settings)
    chunks: list[str] = []
    async for chunk in generate_stream(
        settings,
        project,
        text,
        mode="ask",
        db=db,
        knowledge_base_id=str(bot.kb_id),
        rag_only=True,
        tenant_id=str(bot.tenant_id),
    ):
        chunks.append(chunk)
    answer = "پاسخی از سامانه دریافت نشد. لطفاً دوباره تلاش کنید."
    for event, data in parse_sse_chunks("".join(chunks)):
        if event == "result" and isinstance(data, dict) and data.get("message"):
            answer = str(data["message"])
            break
        if event == "message_done" and isinstance(data, dict) and data.get("message"):
            answer = str(data["message"])
    await send_message(
        api_base=api_base,
        bot_token=token,
        chat_id=chat_id,
        text=answer,
        reply_markup=authed_reply_keyboard(),
    )
    await bot_repo.audit(
        bot.id,
        bot.tenant_id,
        "telegram_chat",
        {"chat_id": chat_id, "update_id": update_id},
    )
    await db.commit()


async def handle_telegram_update(
    db: AsyncSession,
    settings: Settings,
    integration: MessengerIntegration,
    update: dict,
) -> None:
    update_id = int(update.get("update_id") or 0)
    if update_id and not await mark_processed(db, integration.id, update_id):
        logger.info("telegram_update_duplicate", update_id=update_id)
        return

    token = decrypt_secret(settings, integration.bot_token_encrypted)
    if integration.platform == "bale":
        api_base = settings.bale_api_base
    else:
        api_base = settings.telegram_api_base

    bot_repo = OrgBotRepository(db)
    bot = await db.get(OrgBot, integration.org_bot_id)
    iid = str(integration.id)

    # --- callbacks ---
    callback = update.get("callback_query")
    if callback:
        cq_id = str(callback.get("id") or "")
        data = str(callback.get("data") or "")
        msg = callback.get("message") or {}
        chat_id = str((msg.get("chat") or {}).get("id") or "")
        await answer_callback_query(api_base=api_base, bot_token=token, callback_query_id=cq_id)
        if not chat_id or bot is None or not bot.active:
            return
        username = await _resolve_username(api_base=api_base, token=token, integration=integration)
        if data in ("nav:start", "nav:help", "nav:phone"):
            if data == "nav:phone":
                await send_message(
                    api_base=api_base,
                    bot_token=token,
                    chat_id=chat_id,
                    text=f"دکمه «{BTN_SHARE_PHONE}» را بزنید.",
                    reply_markup=guest_reply_keyboard(),
                )
            elif data == "nav:help":
                await send_message(
                    api_base=api_base,
                    bot_token=token,
                    chat_id=chat_id,
                    text=help_message(),
                    reply_markup=guest_reply_keyboard(),
                )
            else:
                await _send_welcome(
                    api_base=api_base,
                    token=token,
                    chat_id=chat_id,
                    bot_title=bot.title,
                    bot_username=username,
                )
        elif data == "nav:admin":
            await set_state(iid, chat_id, state=STATE_AWAIT_ADMIN)
            await send_message(
                api_base=api_base,
                bot_token=token,
                chat_id=chat_id,
                text=admin_code_prompt(),
                reply_markup=guest_reply_keyboard(),
            )
        return

    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        return

    if bot is None or not bot.active:
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=inactive_bot_message(),
        )
        return

    username = await _resolve_username(api_base=api_base, token=token, integration=integration)
    from_user = message.get("from") or {}
    from_id = from_user.get("id")

    # Contact share
    contact = message.get("contact")
    if contact:
        contact_uid = contact.get("user_id")
        if contact_uid is None or from_id is None or int(contact_uid) != int(from_id):
            await send_message(
                api_base=api_base,
                bot_token=token,
                chat_id=chat_id,
                text=contact_rejected_message(),
                reply_markup=guest_reply_keyboard(),
            )
            return
        phone_raw = contact.get("phone_number") or ""
        await _handle_phone_share(
            db=db,
            settings=settings,
            integration=integration,
            bot=bot,
            api_base=api_base,
            token=token,
            chat_id=chat_id,
            phone_raw=phone_raw,
        )
        return

    text = (message.get("text") or "").strip()
    if not text:
        return

    # Button labels (Persian UI)
    if text == BTN_HELP or _normalize_command(text) == "/help":
        authed = await is_chat_authorized(db, integration.id, chat_id)
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=help_message(),
            reply_markup=authed_reply_keyboard() if authed else guest_reply_keyboard(),
        )
        return

    if text == BTN_SHARE_PHONE:
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=f"لطفاً دکمه «{BTN_SHARE_PHONE}» را از کیبورد بزنید (آیکن تماس).",
            reply_markup=guest_reply_keyboard(),
        )
        return

    if text == BTN_ADMIN_CODE or (_normalize_command(text) == "/login" and len(text.split()) == 1):
        await set_state(iid, chat_id, state=STATE_AWAIT_ADMIN)
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=admin_code_prompt(),
            reply_markup=guest_reply_keyboard(),
        )
        return

    cmd = _normalize_command(text)
    if cmd == "/start":
        await set_state(iid, chat_id, state=STATE_GUEST)
        await _send_welcome(
            api_base=api_base,
            token=token,
            chat_id=chat_id,
            bot_title=bot.title,
            bot_username=username,
        )
        return

    if cmd == "/logout" or text == BTN_LOGOUT:
        await deauthorize_chat(db, integration_id=integration.id, chat_id=chat_id)
        await clear_state(iid, chat_id)
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=logout_message(),
            reply_markup=guest_reply_keyboard(),
        )
        return

    if cmd == "/status" or text == BTN_STATUS:
        ok = await is_chat_authorized(db, integration.id, chat_id)
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=status_message(authorized=ok),
            reply_markup=authed_reply_keyboard() if ok else guest_reply_keyboard(),
        )
        return

    if cmd == "/login":
        parts = text.split(maxsplit=1)
        code = parts[1].strip() if len(parts) > 1 else ""
        if not code:
            await set_state(iid, chat_id, state=STATE_AWAIT_ADMIN)
            await send_message(
                api_base=api_base,
                bot_token=token,
                chat_id=chat_id,
                text=admin_code_prompt(),
                reply_markup=guest_reply_keyboard(),
            )
            return
        await _try_login_code(
            db=db,
            integration=integration,
            bot=bot,
            bot_repo=bot_repo,
            api_base=api_base,
            token=token,
            chat_id=chat_id,
            code=code,
        )
        return

    state = await get_state(iid, chat_id)
    st = state.get("state") or STATE_GUEST

    if text == BTN_RESEND and st == STATE_AWAIT_OTP:
        phone = state.get("phone") or ""
        if phone:
            await _handle_phone_share(
                db=db,
                settings=settings,
                integration=integration,
                bot=bot,
                api_base=api_base,
                token=token,
                chat_id=chat_id,
                phone_raw=phone,
            )
        else:
            await send_message(
                api_base=api_base,
                bot_token=token,
                chat_id=chat_id,
                text=f"دوباره «{BTN_SHARE_PHONE}» را بزنید.",
                reply_markup=guest_reply_keyboard(),
            )
        return

    # Await OTP / admin code: accept digit codes
    otp_code = normalize_otp_code(text)
    if st in (STATE_AWAIT_OTP, STATE_AWAIT_ADMIN) and otp_code:
        await _try_login_code(
            db=db,
            integration=integration,
            bot=bot,
            bot_repo=bot_repo,
            api_base=api_base,
            token=token,
            chat_id=chat_id,
            code=otp_code,
        )
        return

    if st == STATE_AWAIT_ADMIN and text and not text.startswith("/"):
        await _try_login_code(
            db=db,
            integration=integration,
            bot=bot,
            bot_repo=bot_repo,
            api_base=api_base,
            token=token,
            chat_id=chat_id,
            code=text,
        )
        return

    # Authorized path
    if not await is_chat_authorized(db, integration.id, chat_id):
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=unauthorized_message(),
            reply_markup=guest_reply_keyboard(),
        )
        return

    await set_state(iid, chat_id, state=STATE_AUTHED)

    if text == BTN_ASK:
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=ask_prompt_message(),
            reply_markup=authed_reply_keyboard(),
        )
        return

    if is_meta_question(text):
        await send_message(
            api_base=api_base,
            bot_token=token,
            chat_id=chat_id,
            text=meta_capabilities_message(bot.title),
            reply_markup=authed_reply_keyboard(),
        )
        return

    await _answer_rag(
        db=db,
        settings=settings,
        bot=bot,
        bot_repo=bot_repo,
        api_base=api_base,
        token=token,
        chat_id=chat_id,
        text=text,
        update_id=update_id,
    )
