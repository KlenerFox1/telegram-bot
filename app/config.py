from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: List[int]
    owner_admin_id: int
    cryptobot_api_key: str

    support_id: str
    channel_id: str
    group_id: str


def load_config() -> Config:
    # .env рядом с main.py
    load_dotenv()

    bot_token = (os.getenv("BOT_TOKEN") or "").strip()
    if not bot_token:
        # interactive fallback (Windows-friendly output)
        print("[WARN] BOT_TOKEN is missing in .env")
        bot_token = input("Enter bot token: ").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is missing")

    owner_admin_id = int(os.getenv("OWNER_ADMIN_ID") or "8693383904")

    admin_ids_raw = (os.getenv("ADMIN_IDS") or "").strip()
    admin_ids: List[int] = []
    if admin_ids_raw:
        for part in admin_ids_raw.split(","):
            part = part.strip()
            if not part:
                continue
            admin_ids.append(int(part))

    if owner_admin_id not in admin_ids:
        admin_ids.append(owner_admin_id)

    return Config(
        bot_token=bot_token,
        admin_ids=admin_ids,
        owner_admin_id=owner_admin_id,
        cryptobot_api_key=(os.getenv("CRYPTOBOT_API_KEY") or "").strip(),
        support_id=os.getenv("SUPPORT_ID", "@support"),
        channel_id=os.getenv("CHANNEL_ID", "@channel"),
        group_id=os.getenv("GROUP_ID", "@group"),
    )

