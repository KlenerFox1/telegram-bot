from __future__ import annotations

import random
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp


class CryptoBotAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": api_key,
            "Content-Type": "application/json",
        }

    async def get_me(self) -> Optional[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/getMe", headers=self.headers) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("ok"):
                    return None
                return data.get("result")

    async def get_balance(self) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/getBalance", headers=self.headers) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                if not data.get("ok"):
                    return []
                return data.get("result", [])

    async def get_asset_balance(self, asset: str = "USDT") -> float:
        balances = await self.get_balance()
        for item in balances:
            if item.get("asset") == asset:
                return float(item.get("available", 0) or 0)
        return 0.0

    async def create_invoice(
        self,
        amount: float,
        asset: str = "USDT",
        description: str = "",
        expires_in_minutes: int = 60,
    ) -> Optional[Dict]:
        payload = {
            "amount": str(amount),
            "asset": asset,
            "description": description[:128],
            "expires_in": int(expires_in_minutes) * 60,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/createInvoice",
                headers=self.headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("ok"):
                    return None
                return data.get("result")

    async def get_invoice_status(self, invoice_id: int) -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/getInvoices",
                headers=self.headers,
                params={"invoice_ids": str(invoice_id)},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("ok"):
                    return None
                items = (data.get("result") or {}).get("items") or []
                if not items:
                    return None
                return items[0].get("status")

    async def transfer(
        self,
        user_id: int,
        amount: float,
        asset: str = "USDT",
        spend_id: Optional[str] = None,
    ) -> Optional[Dict]:
        if not spend_id:
            spend_id = f"withdraw_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
        payload = {"user_id": str(user_id), "amount": str(amount), "asset": asset, "spend_id": spend_id}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/transfer",
                headers=self.headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("ok"):
                    return None
                return data.get("result")

