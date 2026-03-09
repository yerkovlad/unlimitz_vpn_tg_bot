from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import ADMIN_ID
from filters.admin import IsAdmin
from keyboards.inline import *
from db import get_or_create_user
from db.database import SessionFactory

router = Router()


@router.callback_query(F.data == "about_us")
async def about_us_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "📖 <b>About Unlimitz VPN</b>\n\n"
        "We are a team of professionals providing fast, secure and reliable VPN access worldwide.\n\n"
        "🎯 <b>Our mission</b>\n"
        "To give everyone free and unrestricted access to the internet — without censorship, limits or surveillance.\n\n"
        "🔐 <b>Why us?</b>\n"
        "<blockquote>"
        "⚡ Blazing fast speeds\n"
        "🌍 10+ locations worldwide\n"
        "🔒 No logs, full privacy\n"
        "🛟 24/7 support\n"
        "💸 Affordable pricing"
        "</blockquote>\n\n"
        "📢 Follow us: @unlimitzproject\n"
        "🌐 Website: unlimitz.space",
        reply_markup=back_home_inline()
    )
    await call.answer()