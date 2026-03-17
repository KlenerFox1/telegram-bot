from __future__ import annotations

import re
from typing import Any, Dict

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.db import Database
from app.fsm import AdminAccountTypesStates, AdminBroadcastStates
from app.services.broadcast import broadcast_text
from app.ui.keyboards import admin_panel_tiles, account_types_list, back_to
from app.utils import format_number


router = Router()


def _is_admin(cfg: Config, user_id: int) -> bool:
    return user_id in cfg.admin_ids


async def _require_admin(cfg: Config, user_id: int) -> bool:
    return _is_admin(cfg, user_id)


@router.message(Command("admin"))
async def admin_cmd(message: Message, db: Database, cfg: Config):
    if not await _require_admin(cfg, message.from_user.id):
        await message.answer("Нет доступа.")
        return
    await render_admin_panel(message, db=db)


@router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: CallbackQuery, db: Database, cfg: Config):
    if not await _require_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await render_admin_panel(callback.message, db=db)


async def render_admin_panel(message: Message, db: Database) -> None:
    s = await db.get_settings()
    tech = "вкл" if s.get("test_mode") else "выкл"
    stop = "вкл" if s.get("stop_accepting") else "выкл"
    min_wd = float(s.get("min_withdrawal", 1.0) or 1.0)
    fee = float(s.get("withdrawal_fee", 0.03) or 0.03) * 100

    text = (
        "*Настройки*\n\n"
        f"Тех. режим: *{tech}*\n"
        f"Стоп-приём: *{stop}*\n"
        f"Мин. вывод: *{min_wd} USDT*\n"
        f"Комиссия: *{fee:.1f}%*\n"
    )
    await message.answer(text, reply_markup=admin_panel_tiles(), parse_mode="Markdown")


@router.callback_query(F.data == "admin_stop_toggle")
async def admin_stop_toggle(callback: CallbackQuery, db: Database, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    s = await db.get_settings()
    new_value = not bool(s.get("stop_accepting"))
    await db.set_setting("stop_accepting", new_value)
    await callback.answer("Готово")
    await render_admin_panel(callback.message, db=db)


@router.callback_query(F.data == "admin_maintenance")
async def admin_maintenance(callback: CallbackQuery, db: Database, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    s = await db.get_settings()
    text = (
        "*Техобслуживание*\n\n"
        f"Тест-режим: `{s.get('test_mode')}`\n"
        f"Maintenance: `{s.get('maintenance_mode')}`\n"
        f"Стоп-приём: `{s.get('stop_accepting')}`\n"
    )
    await callback.message.edit_text(text, reply_markup=back_to("admin_panel"), parse_mode="Markdown")
    await callback.answer()


# -------- account types --------

@router.callback_query(F.data == "admin_acc_types")
async def acc_types(callback: CallbackQuery, db: Database, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    s = await db.get_settings()
    ats = s.get("account_types") if isinstance(s.get("account_types"), dict) else {}
    await callback.message.edit_text(
        "*Типы аккаунтов*\n\nНажмите на название — изменить цену. 🔄 — переименовать.",
        reply_markup=account_types_list(ats),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_acc_toggle:"))
async def acc_toggle(callback: CallbackQuery, db: Database, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    key = callback.data.split(":", 1)[1]
    s = await db.get_settings()
    ats = s.get("account_types") if isinstance(s.get("account_types"), dict) else {}
    if key not in ats:
        await callback.answer("Не найдено", show_alert=True)
        return
    ats[key]["enabled"] = not bool(ats[key].get("enabled", True))
    await db.set_setting("account_types", ats)
    await callback.answer("Готово")
    await acc_types(callback, db=db, cfg=cfg)


@router.callback_query(F.data.startswith("admin_acc_price:"))
async def acc_price_start(callback: CallbackQuery, state: FSMContext, db: Database, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    key = callback.data.split(":", 1)[1]
    await state.clear()
    await state.update_data(acc_key=key)
    await state.set_state(AdminAccountTypesStates.waiting_new_price)
    await callback.message.edit_text("Введите новую цену в USDT (например `1.50`).", reply_markup=back_to("admin_acc_types"), parse_mode="Markdown")
    await callback.answer()


@router.message(AdminAccountTypesStates.waiting_new_price)
async def acc_price_apply(message: Message, state: FSMContext, db: Database, cfg: Config):
    if not _is_admin(cfg, message.from_user.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return
    data = await state.get_data()
    key = data.get("acc_key")
    try:
        price = float((message.text or "").replace(",", ".").strip())
    except Exception:
        await message.answer("Неверная цена.")
        return
    if price <= 0 or price > 100000:
        await message.answer("Неверная цена.")
        return
    s = await db.get_settings()
    ats = s.get("account_types") if isinstance(s.get("account_types"), dict) else {}
    if key not in ats:
        await message.answer("Тип не найден.")
        await state.clear()
        return
    ats[key]["price"] = round(price, 2)
    await db.set_setting("account_types", ats)
    await state.clear()
    await message.answer("Цена сохранена.")


# -------- broadcast --------

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminBroadcastStates.waiting_text)
    await callback.message.edit_text(
        "*Рассылка*\n\nОтправьте текст для всех пользователей.\nОтмена: `-`",
        reply_markup=back_to("admin_panel"),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_text)
async def broadcast_apply(message: Message, state: FSMContext, db: Database, cfg: Config, bot: Bot):
    if not _is_admin(cfg, message.from_user.id):
        await message.answer("Нет доступа.")
        await state.clear()
        return
    text = (message.text or "").strip()
    if text == "-" or not text:
        await state.clear()
        await message.answer("Отменено.")
        return
    await message.answer("Начинаю рассылку...")
    res = await broadcast_text(db=db, bot=bot, text=text)
    await state.clear()
    await message.answer(
        "Рассылка завершена.\n\n"
        f"Отправлено: {res.sent}\n"
        f"Недоступно: {res.blocked}\n"
        f"Ошибок: {res.failed}"
    )


@router.callback_query(F.data.in_(["admin_params", "admin_promocodes", "admin_blacklist", "admin_disputes", "admin_admins"]))
async def admin_stub(callback: CallbackQuery, cfg: Config):
    if not _is_admin(cfg, callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer("Раздел в разработке", show_alert=True)

