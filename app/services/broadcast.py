from __future__ import annotations

import asyncio
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from app.db import Database
from app.utils import safe_send, sleep_retry_after


@dataclass
class BroadcastResult:
    sent: int = 0
    blocked: int = 0
    failed: int = 0


async def broadcast_text(db: Database, bot: Bot, text: str) -> BroadcastResult:
    res = BroadcastResult()
    user_ids = await db.list_user_ids()

    for uid in user_ids:
        try:
            m = await safe_send(bot, uid, text)
            if m:
                res.sent += 1
            else:
                res.blocked += 1
        except TelegramRetryAfter as e:
            await sleep_retry_after(e)
            try:
                m = await safe_send(bot, uid, text)
                if m:
                    res.sent += 1
                else:
                    res.blocked += 1
            except Exception:
                res.failed += 1
        except Exception:
            res.failed += 1

        await asyncio.sleep(0.05)

    return res

