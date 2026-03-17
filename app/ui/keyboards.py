from __future__ import annotations

from typing import Any, Dict, List, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def back_to(callback: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=callback), width=1)
    return b.as_markup()


def main_menu(is_admin: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💼 Продать аккаунт", callback_data="nav_sell"),
        InlineKeyboardButton(text="📋 Мои заявки", callback_data="nav_my_requests"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="nav_profile"),
        InlineKeyboardButton(text="💰 Баланс", callback_data="nav_balance"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="💸 Вывести", callback_data="nav_withdraw"),
        InlineKeyboardButton(text="📥 Пополнить", callback_data="nav_deposit"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="nav_support"),
        width=1,
    )
    if is_admin:
        b.row(InlineKeyboardButton(text="⚙️ Админка", callback_data="admin_panel"), width=1)
    return b.as_markup()


def admin_panel_tiles() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 Типы аккаунтов", callback_data="admin_acc_types"),
        InlineKeyboardButton(text="👑 Администраторы", callback_data="admin_admins"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="🔧 Параметры", callback_data="admin_params"),
        InlineKeyboardButton(text="🛠 Техобслуживание", callback_data="admin_maintenance"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="🛑 Стоп-приём", callback_data="admin_stop_toggle"),
        InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin_promocodes"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="⛔ Чёрный список", callback_data="admin_blacklist"),
        InlineKeyboardButton(text="⚡ Споры", callback_data="admin_disputes"),
        width=2,
    )
    b.row(
        InlineKeyboardButton(text="📤 Экспорт CSV", callback_data="admin_export_csv"),
        InlineKeyboardButton(text="💾 Бэкап БД", callback_data="admin_backup_db"),
        width=2,
    )
    b.row(InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast"), width=1)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"), width=1)
    return b.as_markup()


def account_types_list(account_types: Dict[str, Dict[str, Any]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, meta in account_types.items():
        enabled = bool(meta.get("enabled", True))
        label = str(meta.get("label", key))
        price = float(meta.get("price", 1.00) or 1.00)
        b.row(
            InlineKeyboardButton(text="✅" if enabled else "❌", callback_data=f"admin_acc_toggle:{key}"),
            InlineKeyboardButton(
                text=f"{(label[:12] + '…' if len(label) > 13 else label)} {price:.2f}$",
                callback_data=f"admin_acc_price:{key}",
            ),
            InlineKeyboardButton(text="🔄", callback_data=f"admin_acc_rename:{key}"),
            InlineKeyboardButton(text="🗑", callback_data=f"admin_acc_delete:{key}"),
            width=4,
        )
    b.row(InlineKeyboardButton(text="➕ Добавить тип", callback_data="admin_acc_add"), width=1)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel"), width=1)
    return b.as_markup()


def sell_types(enabled_types: List[Tuple[str, Dict[str, Any]]]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, meta in enabled_types[:24]:
        label = str(meta.get("label", key))
        price = float(meta.get("price", 1.00) or 1.00)
        b.row(InlineKeyboardButton(text=f"{label} — {price:.2f} USDT", callback_data=f"sell_type:{key}"), width=1)
    b.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"), width=1)
    return b.as_markup()

