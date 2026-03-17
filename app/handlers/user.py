from __future__ import annotations

from typing import Any, Dict, List, Tuple

from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.config import Config
from app.db import Database
from app.fsm import SellStates
from app.models import RequestStatus
from app.ui.keyboards import main_menu, sell_types, back_to
from app.utils import format_number, format_phone, now_iso, safe_send


router = Router()


def _is_admin(cfg: Config, user_id: int) -> bool:
    return user_id in cfg.admin_ids


@router.message(Command("start"))
async def start_cmd(message: Message, command: CommandObject, db: Database, cfg: Config):
    tg = message.from_user
    user = await db.get_user(tg.id)
    user.username = tg.username or ""
    user.first_name = tg.first_name or ""
    user.last_name = tg.last_name or ""
    user.last_activity = now_iso()
    await db.upsert_user(user)

    await show_main(message, db=db, cfg=cfg)


async def show_main(message: Message, db: Database, cfg: Config) -> None:
    user = await db.get_user(message.from_user.id)
    text = (
        "*Главное меню*\n\n"
        f"Баланс: `{format_number(user.balance)} USDT`\n"
        f"Бонус: `{format_number(user.bonus_balance)} USDT`\n"
    )
    await message.answer(text, reply_markup=main_menu(_is_admin(cfg, user.id)), parse_mode="Markdown")


@router.callback_query(F.data == "main_menu")
async def main_menu_cb(callback: CallbackQuery, db: Database, cfg: Config):
    await callback.answer()
    await show_main(callback.message, db=db, cfg=cfg)


def _enabled_types(settings: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    ats = settings.get("account_types") or {}
    out: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(ats, dict):
        for k, v in ats.items():
            if isinstance(v, dict) and bool(v.get("enabled", True)):
                out.append((k, v))
    return out


@router.callback_query(F.data == "nav_sell")
async def sell_start(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    settings = await db.get_settings()
    enabled = _enabled_types(settings)
    if not enabled:
        await callback.message.edit_text("Нет доступных типов. Админ должен включить их.", reply_markup=back_to("main_menu"))
        return
    await state.clear()
    await state.set_state(SellStates.waiting_type)
    await callback.message.edit_text(
        "*Продать аккаунт*\n\nВыберите тип:",
        reply_markup=sell_types(enabled),
        parse_mode="Markdown",
    )


@router.callback_query(SellStates.waiting_type, F.data.startswith("sell_type:"))
async def sell_choose_type(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.answer()
    key = callback.data.split(":", 1)[1]
    settings = await db.get_settings()
    ats = settings.get("account_types") or {}
    meta = (ats.get(key) if isinstance(ats, dict) else None) or {}
    if not meta or not bool(meta.get("enabled", True)):
        await callback.answer("Тип недоступен", show_alert=True)
        return
    await state.update_data(acc_type=key)
    await state.set_state(SellStates.waiting_phone)
    await callback.message.edit_text("Введите номер телефона (пример `+79991234567`).", reply_markup=back_to("main_menu"), parse_mode="Markdown")


@router.message(SellStates.waiting_phone)
async def sell_phone(message: Message, state: FSMContext, db: Database, bot: Bot, cfg: Config):
    phone = format_phone((message.text or "").strip())
    if not phone or not phone.lstrip("+").isdigit() or not (10 <= len(phone.lstrip("+")) <= 15):
        await message.answer("Неверный номер. Пример: `+79991234567`", parse_mode="Markdown")
        return

    data = await state.get_data()
    acc_type = data.get("acc_type")
    if not acc_type:
        await state.clear()
        await show_main(message, db=db, cfg=cfg)
        return

    settings = await db.get_settings()
    meta = (settings.get("account_types") or {}).get(acc_type, {}) if isinstance(settings.get("account_types"), dict) else {}
    label = str(meta.get("label", acc_type))
    price = float(meta.get("price", 1.00) or 1.00)

    req = await db.create_request(
        user_id=message.from_user.id,
        account_type=acc_type,
        phone_number=phone,
        price=price,
    )
    req.logs.append({"ts": now_iso(), "event": "created", "type": acc_type, "price": price})
    await db.upsert_request(req)

    await state.clear()
    await message.answer(
        f"Заявка создана: *#{req.id}*\n"
        f"Тип: *{label}*\n"
        f"Номер: `{phone}`\n"
        f"Цена: *{price:.2f} USDT*\n\n"
        "Ожидайте проверки администратором.",
        parse_mode="Markdown",
        reply_markup=main_menu(_is_admin(cfg, message.from_user.id)),
    )

    # уведомление админам (карточку и кнопки добавим в admin handler)
    for admin_id in cfg.admin_ids:
        await safe_send(
            bot,
            admin_id,
            f"Новая заявка #{req.id}\n{label}\n{phone}\n{price:.2f} USDT",
        )


@router.callback_query(F.data.startswith("nav_"))
async def nav_stub(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Раздел в разработке.", reply_markup=back_to("main_menu"))

