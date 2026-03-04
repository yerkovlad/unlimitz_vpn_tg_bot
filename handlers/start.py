from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from keyboards.reply import main_menu
from keyboards.inline import *

from db import get_or_create_user
from db.database import SessionFactory
from db.crud import create_referral

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
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != message.from_user.id:
                await create_referral(session, referrer_id, message.from_user.id)

    await message.answer(WELCOME_TEXT, reply_markup=menu_inline())


@router.callback_query(F.data == "back_home")
async def back_home_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(WELCOME_TEXT, reply_markup=menu_inline())
    await call.answer()


@router.callback_query(F.data == "close")
async def callback_close(call: CallbackQuery):
    await call.message.delete()
    await call.answer()