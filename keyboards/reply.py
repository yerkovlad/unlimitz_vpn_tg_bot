from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="ℹ️ О боте"), KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="✍️ Отзыв")], [KeyboardButton(text="Получить Vless")]
        ],
        resize_keyboard=True
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()