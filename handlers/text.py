from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from keyboards.reply import main_menu
from keyboards.inline import about_inline
from vless.api import generate_vless_link

router = Router()


@router.message(F.text == "Получить Vless")
async def btn_about(message: Message):
    link = await generate_vless_link("username")
    if link:
        await message.answer(link)
    else:
        await message.answer("❌ Ошибка при создании ссылки")