from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import SessionFactory
from db.crud import set_user_lang
from db.models import User
from locales import t

router = Router()


def lang_inline(current_lang: str = "ru") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    langs = [("🇷🇺 Русский", "ru"), ("🇺🇦 Українська", "uk"), ("🇬🇧 English", "en")]
    for name, code in langs:
        check = "✅ " if code == current_lang else ""
        builder.add(InlineKeyboardButton(
            text=f"{check}{name}",
            callback_data=f"set_lang:{code}"
        ))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠", callback_data="back_home"))
    return builder.as_markup()


@router.callback_query(F.data == "change_lang")
async def change_lang_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        user = await session.get(User, call.from_user.id)
        lang = user.lang if user else "ru"

    await call.message.delete()
    await call.message.answer(
        t("choose_lang", lang),
        reply_markup=lang_inline(lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("set_lang:"))
async def set_lang_callback(call: CallbackQuery):
    lang = call.data.split(":")[1]
    async with SessionFactory() as session:
        await set_user_lang(session, call.from_user.id, lang)

    await call.message.delete()
    await call.message.answer(
        t("lang_set", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home")]
        ])
    )
    await call.answer()