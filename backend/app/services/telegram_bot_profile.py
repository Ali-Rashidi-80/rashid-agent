"""Persian bot copy, keyboards, and Bot API profile applicator."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

_LRI = "\u2066"
_PDI = "\u2069"

BOT_DISPLAY_NAME = "دستیار دانش | موسسه حقوقی عدل امید"

BOT_SHORT_DESCRIPTION = (
    "پاسخ فقط از اسناد رسمی پایگاه دانش موسسه حقوقی عدل امید — ورود با موبایل یا کد ادمین."
)

BOT_DESCRIPTION = (
    "دستیار پایگاه دانش رسمی موسسه حقوقی عدل امید.\n"
    "\n"
    "پاسخ فقط از اسناد بارگذاری‌شده؛ مشاوره خارج از اسناد ارائه نمی‌شود.\n"
    "\n"
    "ورود:\n"
    "۱) اشتراک شماره موبایل (اگر در لیست مجاز باشید، کد پیامک می‌شود)\n"
    "۲) یا ورود با کد ادمین\n"
    "۳) پرسش خود را بفرستید\n"
    "\n"
    "وبسایت: https://adlomid.com\n"
    "سامانه: https://adlomidapp.com"
)

BOT_COMMANDS: list[dict[str, str]] = [
    {"command": "start", "description": "شروع و منوی ورود"},
    {"command": "help", "description": "راهنمای استفاده"},
    {"command": "login", "description": "ورود با کد ادمین"},
    {"command": "status", "description": "وضعیت ورود"},
    {"command": "logout", "description": "خروج"},
]

BTN_SHARE_PHONE = "اشتراک شماره موبایل"
BTN_ADMIN_CODE = "ورود با کد ادمین"
BTN_HELP = "راهنما"
BTN_STATUS = "وضعیت"
BTN_LOGOUT = "خروج"
BTN_ASK = "پرسش جدید"
BTN_RESEND = "ارسال مجدد کد"

BOTFATHER_PASTE: dict[str, Any] = {
    "profile_name": BOT_DISPLAY_NAME,
    "profile_about": "دستیار پایگاه دانش رسمی موسسه حقوقی عدل امید",
    "welcome_description": BOT_DESCRIPTION,
    "commands": [
        {"command": f"/{c['command']}", "description": c["description"]} for c in BOT_COMMANDS
    ],
    "direct_links": [
        {
            "slug": "adlomid",
            "url": "https://adlomid.com/",
            "title": "وبسایت هلدینگ حقوقی عدل امید",
            "description": "مرکز جامع خدمات حقوقی، مالی و آموزشی با رویکرد تخصصی.",
        },
        {
            "slug": "adlomidapp",
            "url": "https://adlomidapp.com/",
            "title": "سامانه یکپارچه موسسه حقوقی عدل امید",
            "description": "خدمات وکالت مدرن و مدیریت پرونده در یک سامانه یکپارچه.",
        },
    ],
}


def cmd(name: str) -> str:
    bare = name if name.startswith("/") else f"/{name}"
    return f"{_LRI}{bare}{_PDI}"


def guest_reply_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": BTN_SHARE_PHONE, "request_contact": True}],
            [{"text": BTN_ADMIN_CODE}, {"text": BTN_HELP}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "شماره را به اشتراک بگذارید یا کد ادمین را بفرستید…",
    }


def await_otp_reply_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": BTN_RESEND}],
            [{"text": BTN_ADMIN_CODE}, {"text": BTN_HELP}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "کد پیامک‌شده را وارد کنید…",
    }


def authed_reply_keyboard() -> dict[str, Any]:
    return {
        "keyboard": [
            [{"text": BTN_ASK}],
            [{"text": BTN_STATUS}, {"text": BTN_HELP}],
            [{"text": BTN_LOGOUT}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "پرسش خود را بنویسید…",
    }


def remove_keyboard() -> dict[str, Any]:
    return {"remove_keyboard": True}


def guest_inline_keyboard(bot_username: str | None = None) -> dict[str, Any]:
    rows: list[list[dict[str, str]]] = [
        [{"text": "ورود با موبایل", "callback_data": "nav:phone"}],
        [{"text": "کد ادمین", "callback_data": "nav:admin"}],
        [{"text": "راهنما", "callback_data": "nav:help"}],
    ]
    if bot_username:
        u = bot_username.lstrip("@")
        rows.insert(0, [{"text": "شروع مجدد", "url": f"https://t.me/{u}?start=guide"}])
    return {"inline_keyboard": rows}


def welcome_message(bot_title: str) -> str:
    title = (bot_title or BOT_DISPLAY_NAME).strip()
    return (
        f"«{title}»\n"
        "\n"
        "پاسخ‌ها فقط از اسناد رسمی پایگاه دانش است.\n"
        "\n"
        "برای ورود یکی را انتخاب کنید:\n"
        f"• دکمه «{BTN_SHARE_PHONE}» — اگر شماره شما مجاز باشد، کد پیامک می‌شود\n"
        f"• «{BTN_ADMIN_CODE}» — کد یک‌بارمصرف ادمین\n"
        "\n"
        f"راهنما: {BTN_HELP}"
    )


def help_message() -> str:
    return (
        "راهنمای کوتاه\n"
        "\n"
        "۱) ورود با اشتراک شماره موبایل یا کد ادمین\n"
        "۲) پس از ورود، سؤال خود را بفرستید\n"
        "۳) پاسخ فقط از اسناد پایگاه دانش است\n"
        "\n"
        f"دستورات: {cmd('start')} · {cmd('help')} · {cmd('login')} · {cmd('status')} · {cmd('logout')}"
    )


def meta_capabilities_message(bot_title: str) -> str:
    return (
        f"«{(bot_title or BOT_DISPLAY_NAME).strip()}»\n"
        "\n"
        "این دستیار به پرسش‌های شما فقط بر اساس اسناد و بخشنامه‌های "
        "بارگذاری‌شده در پایگاه دانش پاسخ می‌دهد.\n"
        "مشاوره یا اظهارنظر خارج از اسناد رسمی ارائه نمی‌شود.\n"
        "\n"
        f"{help_message()}"
    )


def admin_code_prompt() -> str:
    return (
        "کد یک‌بارمصرف یا رمز ادمین را بفرستید.\n"
        f"یا با دستور: {cmd('login')} کد"
    )


def otp_sent_message() -> str:
    return (
        "اگر شماره شما در فهرست مجاز باشد، کد یک‌بارمصرف پیامک شده است.\n"
        "کد را همین‌جا بفرستید.\n"
        f"ارسال مجدد: {BTN_RESEND}"
    )


def otp_failed_message() -> str:
    return "ارسال پیامک موقتاً ممکن نیست. کمی بعد دوباره تلاش کنید یا با کد ادمین وارد شوید."


def contact_rejected_message() -> str:
    return "فقط شمارهٔ خودتان را از دکمهٔ اشتراک شماره ارسال کنید."


def login_success_message() -> str:
    return "ورود موفق. پرسش خود را بنویسید."


def login_failed_message() -> str:
    return "کد نامعتبر یا منقضی است. دوباره تلاش کنید."


def unauthorized_message() -> str:
    return f"ابتدا وارد شوید: «{BTN_SHARE_PHONE}» یا «{BTN_ADMIN_CODE}»"


def logout_message() -> str:
    return "خارج شدید. برای ورود دوباره از منوی پایین استفاده کنید."


def status_message(*, authorized: bool) -> str:
    if authorized:
        return "وضعیت: وارد شده‌اید — می‌توانید پرسش بفرستید."
    return "وضعیت: وارد نشده‌اید."


def inactive_bot_message() -> str:
    return "این دستیار فعلاً در دسترس نیست."


def ask_prompt_message() -> str:
    return "پرسش خود را بنویسید؛ پاسخ فقط از اسناد پایگاه دانش است."


def is_meta_question(text: str) -> bool:
    t = (text or "").strip().lower()
    needles = (
        "what can this bot do",
        "what can you do",
        "این بات چه",
        "این ربات چه",
        "چه کار می‌کنی",
        "چه کار ميکني",
        "قابلیت",
        "راهنما",
    )
    return any(n in t for n in needles)


async def _tg_post(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    bot_token: str,
    method: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/bot{bot_token}/{method}"
    resp = await client.post(url, json=payload or {})
    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not resp.is_success or not data.get("ok"):
        logger.warning(
            "telegram_profile_api_failed",
            method=method,
            status=resp.status_code,
            body=str(data or resp.text)[:400],
        )
        return {"ok": False, "method": method, "status": resp.status_code, "body": data}
    return {"ok": True, "method": method, "result": data.get("result")}


async def apply_bot_profile(
    *,
    bot_token: str,
    api_base: str = "https://api.telegram.org",
    language_code: str | None = "fa",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    lang: dict[str, Any] = {}
    if language_code:
        lang["language_code"] = language_code

    async with httpx.AsyncClient(timeout=45.0) as client:
        me = await _tg_post(client, api_base=api_base, bot_token=bot_token, method="getMe")
        results.append(me)
        for method, payload in (
            ("setMyName", {"name": BOT_DISPLAY_NAME, **lang}),
            ("setMyName", {"name": BOT_DISPLAY_NAME}),
            ("setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION, **lang}),
            ("setMyShortDescription", {"short_description": BOT_SHORT_DESCRIPTION}),
            ("setMyDescription", {"description": BOT_DESCRIPTION, **lang}),
            ("setMyDescription", {"description": BOT_DESCRIPTION}),
            ("setMyCommands", {"commands": BOT_COMMANDS, **lang}),
            ("setMyCommands", {"commands": BOT_COMMANDS}),
        ):
            results.append(
                await _tg_post(
                    client,
                    api_base=api_base,
                    bot_token=bot_token,
                    method=method,
                    payload=payload,
                )
            )
    return results
