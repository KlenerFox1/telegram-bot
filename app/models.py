from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class User:
    id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    balance: float = 0.0
    bonus_balance: float = 0.0
    frozen_balance: float = 0.0
    total_deposits: float = 0.0
    total_withdrawals: float = 0.0
    cryptobot_id: Optional[int] = None
    referral_code: str = ""
    registration_date: str = ""
    last_activity: str = ""
    is_blocked: bool = False


@dataclass
class AccountRequest:
    id: int
    user_id: int
    account_type: str
    phone_number: str
    price: float
    status: RequestStatus = RequestStatus.PENDING
    created_at: str = ""
    updated_at: str = ""
    is_unregistered: bool = False
    is_vip: bool = False
    admin_note: str = ""
    logs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CryptoBotInvoice:
    invoice_id: int
    user_id: int
    amount: float
    asset: str
    status: str
    pay_url: str
    created_at: str
    expires_at: str
    paid_at: Optional[str] = None
    purpose: Optional[str] = None
    credited: bool = False


@dataclass
class Withdrawal:
    id: int
    user_id: int
    amount: float
    net_amount: float
    fee: float
    status: PaymentStatus = PaymentStatus.PENDING
    wallet: str = ""
    created_at: str = ""
    processed_at: Optional[str] = None
    cryptobot_transfer_id: Optional[int] = None
    comment: str = ""

