from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from keyboards.reply import main_menu
from keyboards.inline import *

from db import get_or_create_user
from db.database import SessionFactory

router = Router()

WELCOME_TEXT = (
    "🚀 <b>Unlimitz VPN — Fast & Secure Access</b>\n\n"
    "🌍 <b>Locations:</b>"
    "<blockquote>"
    "🇩🇪 Germany, 🇳🇱 Netherlands, 🇺🇸 USA, 🇵🇱 Poland, "
    "🇹🇷 Turkey, 🇫🇮 Finland, 🇸🇪 Sweden, "
    "🇯🇵 Japan, 🇰🇿 Kazakhstan, 🇮🇳 India"
    "</blockquote>\n\n"
    "💎 <b>Benefits:</b>"
    "<blockquote>"
    "⚡ Maximum speed\n"
    "🎬 4K streaming\n"
    "🔒 Full anonymity\n"
    "👆 1-click connection"
    "</blockquote>\n\n"
    "👇 Choose an action:"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with SessionFactory() as session:
        await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username
        )

    await message.answer(WELCOME_TEXT, reply_markup=menu_inline())


@router.callback_query(F.data == "back_home")
async def back_home_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(WELCOME_TEXT, reply_markup=menu_inline())
    await call.answer()


# @router.message(F.text == "ℹ️ О боте")
# async def btn_about(message: Message):
#     await message.answer(
#         "ℹ️ <b>About the bot</b>\n\n"
#         "Template bot built with <b>aiogram 3.x</b>\n"
#         "Folder structure, FSM, middleware and inline keyboards.",
#         reply_markup=about_inline()
#     )


@router.callback_query(F.data == "close")
async def callback_close(call: CallbackQuery):
    await call.message.delete()
    await call.answer()