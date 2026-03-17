from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from app.models import (
    AccountRequest,
    CryptoBotInvoice,
    PaymentStatus,
    RequestStatus,
    User,
    Withdrawal,
)
from app.utils import now_iso


DEFAULT_SETTINGS: Dict[str, Any] = {
    "treasury_balance": 10000.0,
    "min_withdrawal": 1.0,
    "max_withdrawal": 10000.0,
    "withdrawal_fee": 0.03,
    "test_mode": False,
    "maintenance_mode": False,
    "stop_accepting": False,
    "cryptobot_enabled": False,
    "auto_withdraw_enabled": True,
    "account_types": {
        "tg": {"label": "Telegram", "enabled": True, "price": 1.00},
        "vk": {"label": "VKONTAKTE", "enabled": True, "price": 1.00},
        "ig": {"label": "Instagram", "enabled": True, "price": 1.00},
        "other": {"label": "Other", "enabled": True, "price": 1.00},
    },
}


class Database:
    def __init__(self, path: str = "bot_database.db"):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL,
                    bonus_balance REAL,
                    frozen_balance REAL,
                    total_deposits REAL,
                    total_withdrawals REAL,
                    cryptobot_id INTEGER,
                    referral_code TEXT,
                    registration_date TEXT,
                    last_activity TEXT,
                    is_blocked INTEGER
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    account_type TEXT,
                    phone_number TEXT,
                    price REAL,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    is_unregistered INTEGER,
                    is_vip INTEGER,
                    admin_note TEXT,
                    logs TEXT
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cryptobot_invoices (
                    invoice_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    asset TEXT,
                    status TEXT,
                    pay_url TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    paid_at TEXT,
                    purpose TEXT,
                    credited INTEGER DEFAULT 0
                )
                """
            )

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    amount REAL,
                    net_amount REAL,
                    fee REAL,
                    status TEXT,
                    wallet TEXT,
                    created_at TEXT,
                    processed_at TEXT,
                    cryptobot_transfer_id INTEGER,
                    comment TEXT
                )
                """
            )

            await db.commit()

    # ---------------- settings ----------------
    async def get_settings(self) -> Dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT key, value FROM settings")
            rows = await cur.fetchall()
            for k, v in rows:
                try:
                    settings[k] = json.loads(v)
                except Exception:
                    settings[k] = v
        # миграция account_types: добавить price
        ats = settings.get("account_types")
        if isinstance(ats, dict):
            changed = False
            for _, meta in ats.items():
                if isinstance(meta, dict) and "price" not in meta:
                    meta["price"] = 1.00
                    changed = True
            if changed:
                settings["account_types"] = ats
                await self.set_setting("account_types", ats)
        return settings

    async def set_setting(self, key: str, value: Any) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(value), now_iso()),
            )
            await db.commit()

    # ---------------- users ----------------
    async def upsert_user(self, user: User) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO users VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    user.id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.balance,
                    user.bonus_balance,
                    user.frozen_balance,
                    user.total_deposits,
                    user.total_withdrawals,
                    user.cryptobot_id,
                    user.referral_code,
                    user.registration_date,
                    user.last_activity,
                    1 if user.is_blocked else 0,
                ),
            )
            await db.commit()

    async def get_user(self, user_id: int) -> User:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cur.fetchone()
            if not row:
                user = User(
                    id=user_id,
                    registration_date=now_iso(),
                    last_activity=now_iso(),
                )
                await self.upsert_user(user)
                return user
            return User(
                id=row["id"],
                username=row["username"] or "",
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                balance=row["balance"] or 0.0,
                bonus_balance=row["bonus_balance"] or 0.0,
                frozen_balance=row["frozen_balance"] or 0.0,
                total_deposits=row["total_deposits"] or 0.0,
                total_withdrawals=row["total_withdrawals"] or 0.0,
                cryptobot_id=row["cryptobot_id"],
                referral_code=row["referral_code"] or "",
                registration_date=row["registration_date"] or "",
                last_activity=row["last_activity"] or "",
                is_blocked=bool(row["is_blocked"]),
            )

    async def list_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT id FROM users")
            rows = await cur.fetchall()
            return [int(r[0]) for r in rows]

    async def add_balance(self, user_id: int, amount: float) -> None:
        user = await self.get_user(user_id)
        user.balance += float(amount)
        user.total_deposits += float(amount)
        user.last_activity = now_iso()
        await self.upsert_user(user)

    # ---------------- requests ----------------
    async def next_request_id(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT MAX(id) FROM requests")
            row = await cur.fetchone()
            return int((row[0] or 0) + 1)

    async def create_request(
        self,
        user_id: int,
        account_type: str,
        phone_number: str,
        price: float,
    ) -> AccountRequest:
        rid = await self.next_request_id()
        now = now_iso()
        req = AccountRequest(
            id=rid,
            user_id=user_id,
            account_type=account_type,
            phone_number=phone_number,
            price=float(price),
            status=RequestStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        await self.upsert_request(req)
        return req

    async def upsert_request(self, req: AccountRequest) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO requests VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    req.id,
                    req.user_id,
                    req.account_type,
                    req.phone_number,
                    req.price,
                    req.status.value,
                    req.created_at,
                    req.updated_at,
                    1 if req.is_unregistered else 0,
                    1 if req.is_vip else 0,
                    req.admin_note,
                    json.dumps(req.logs),
                ),
            )
            await db.commit()

    async def get_request(self, request_id: int) -> Optional[AccountRequest]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
            row = await cur.fetchone()
            if not row:
                return None
            return AccountRequest(
                id=row["id"],
                user_id=row["user_id"],
                account_type=row["account_type"],
                phone_number=row["phone_number"],
                price=row["price"] or 0.0,
                status=RequestStatus(row["status"]),
                created_at=row["created_at"] or "",
                updated_at=row["updated_at"] or "",
                is_unregistered=bool(row["is_unregistered"]),
                is_vip=bool(row["is_vip"]),
                admin_note=row["admin_note"] or "",
                logs=json.loads(row["logs"]) if row["logs"] else [],
            )

    # ---------------- invoices ----------------
    async def upsert_invoice(self, inv: CryptoBotInvoice) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cryptobot_invoices (
                    invoice_id, user_id, amount, asset, status, pay_url,
                    created_at, expires_at, paid_at, purpose, credited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inv.invoice_id,
                    inv.user_id,
                    inv.amount,
                    inv.asset,
                    inv.status,
                    inv.pay_url,
                    inv.created_at,
                    inv.expires_at,
                    inv.paid_at,
                    inv.purpose,
                    1 if inv.credited else 0,
                ),
            )
            await db.commit()

    async def get_invoice(self, invoice_id: int) -> Optional[CryptoBotInvoice]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM cryptobot_invoices WHERE invoice_id = ?",
                (invoice_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            return CryptoBotInvoice(
                invoice_id=row["invoice_id"],
                user_id=row["user_id"],
                amount=row["amount"] or 0.0,
                asset=row["asset"] or "USDT",
                status=row["status"] or "active",
                pay_url=row["pay_url"] or "",
                created_at=row["created_at"] or "",
                expires_at=row["expires_at"] or "",
                paid_at=row["paid_at"],
                purpose=row["purpose"],
                credited=bool(row["credited"]),
            )

    # ---------------- withdrawals (simplified) ----------------
    async def next_withdrawal_id(self) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT MAX(id) FROM withdrawals")
            row = await cur.fetchone()
            return int((row[0] or 0) + 1)

    async def create_withdrawal(
        self,
        user_id: int,
        amount: float,
        wallet: str,
        fee_rate: float,
    ) -> Optional[Withdrawal]:
        settings = await self.get_settings()
        if amount < float(settings.get("min_withdrawal", 0)) or amount > float(settings.get("max_withdrawal", 1e9)):
            return None

        user = await self.get_user(user_id)
        if user.balance < amount:
            return None

        fee = float(amount) * float(fee_rate)
        net = float(amount) - fee
        wid = await self.next_withdrawal_id()
        wd = Withdrawal(
            id=wid,
            user_id=user_id,
            amount=float(amount),
            net_amount=net,
            fee=fee,
            status=PaymentStatus.PENDING,
            wallet=wallet,
            created_at=now_iso(),
        )

        user.balance -= float(amount)
        user.frozen_balance += float(amount)
        await self.upsert_user(user)
        await self.upsert_withdrawal(wd)
        return wd

    async def upsert_withdrawal(self, wd: Withdrawal) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO withdrawals VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    wd.id,
                    wd.user_id,
                    wd.amount,
                    wd.net_amount,
                    wd.fee,
                    wd.status.value,
                    wd.wallet,
                    wd.created_at,
                    wd.processed_at,
                    wd.cryptobot_transfer_id,
                    wd.comment,
                ),
            )
            await db.commit()

