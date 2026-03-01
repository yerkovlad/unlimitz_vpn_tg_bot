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


@router.callback_query(F.data == "earn")
async def earn_callback(call: CallbackQuery):
    await call.answer("🧑‍💻 In progress", show_alert=False)