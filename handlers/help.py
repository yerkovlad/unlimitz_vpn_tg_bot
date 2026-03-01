from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from keyboards.reply import main_menu

router = Router()


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        "/start — главное меню\n"
        "/help — это сообщение\n"
        "/admin — панель админа\n\n"
        "Используй кнопки внизу для навигации.",
        reply_markup=main_menu()
    )