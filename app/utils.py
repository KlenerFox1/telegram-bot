from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import Message


def format_number(number: float) -> str:
    return f"{number:,.2f}".replace(",", " ")


def format_phone(phone: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    elif not cleaned.startswith("+") and len(cleaned) == 10:
        cleaned = "+7" + cleaned
    return cleaned


def now_iso() -> str:
    return datetime.now().isoformat()


async def safe_edit(message: Message, text: str, reply_markup=None, **kwargs) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def safe_send(bot: Bot, user_id: int, text: str, **kwargs) -> Optional[Message]:
    try:
        return await bot.send_message(user_id, text, **kwargs)
    except TelegramForbiddenError:
        return None


async def sleep_retry_after(exc: TelegramRetryAfter) -> None:
    await asyncio.sleep(int(getattr(exc, "retry_after", 1)) + 1)

