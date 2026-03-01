from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from keyboards.reply import main_menu, cancel_menu

router = Router()


class FeedbackState(StatesGroup):
    waiting_for_text = State()


@router.message(F.text == "✍️ Отзыв")
async def btn_feedback(message: Message, state: FSMContext):
    await message.answer(
        "✍️ Напиши свой отзыв, я передам его администратору.\n"
        "Или нажми <b>Отмена</b>.",
        reply_markup=cancel_menu()
    )
    await state.set_state(FeedbackState.waiting_for_text)


@router.message(F.text == "❌ Отмена", FeedbackState.waiting_for_text)
async def cancel_feedback(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


@router.message(FeedbackState.waiting_for_text)
async def process_feedback(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer("✅ Спасибо! Твой отзыв отправлен.", reply_markup=main_menu())
    await bot.send_message(
        ADMIN_ID,
        f"📩 <b>Новый отзыв</b>\n"
        f"От: @{message.from_user.username} (id: <code>{message.from_user.id}</code>)\n\n"
        f"{message.text}"
    )