from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import ADMIN_ID
from keyboards.inline import profile_keyboard_inline
from db import get_or_create_user
from db.database import SessionFactory
from db.crud import get_user_lang
from locales import t

router = Router()


@router.callback_query(F.data == "profile")
async def profile_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        user = await get_or_create_user(
            session,
            user_id=call.from_user.id,
            username=call.from_user.username
        )
        lang = user.lang or "en"

    username = f"@{user.username}" if user.username else "—"

    builder = InlineKeyboardBuilder()
    # существующие кнопки профиля
    is_admin = call.from_user.id == int(ADMIN_ID)
    kb = profile_keyboard_inline(is_admin=is_admin, lang=lang)
    for row in kb.inline_keyboard:
        builder.row(*row)
    # кнопка смены языка
    builder.row(InlineKeyboardButton(
        text=t("btn_change_lang", lang),
        callback_data="change_lang"
    ))

    await call.message.delete()
    await call.message.answer(
        t("profile", lang,
          user_id=user.id,
          balance=round(user.balance, 2),
          ref_balance=round(user.ref_balance, 2)) +
        f"\n👤 Username: {username}",
        reply_markup=builder.as_markup()
    )
    await call.answer()