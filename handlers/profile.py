from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import ADMIN_ID
from filters.admin import IsAdmin
from keyboards.inline import *
from db import get_or_create_user
from db.database import SessionFactory

router = Router()
router.message.filter(IsAdmin())


@router.callback_query(F.data == "profile")
async def profile_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        user = await get_or_create_user(
            session,
            user_id=call.from_user.id,
            username=call.from_user.username
        )

    username = f"@{user.username}" if user.username else "—"

    await call.message.delete()
    await call.message.answer(
        "👤 <b>Profile:</b>\n\n"
        f"🆔 Id: <code>{user.id}</code>\n"
        f"👤 Username: {username}\n"
        f"💲 Balance: <code>{user.balance} $</code>",
        reply_markup=profile_keyboard_inline(is_admin=call.from_user.id == int(ADMIN_ID))
    )
    await call.answer()