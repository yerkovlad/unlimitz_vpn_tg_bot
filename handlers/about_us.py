from aiogram import Router, F
from aiogram.types import CallbackQuery

from db.database import SessionFactory
from db.crud import get_user_lang
from keyboards.inline import back_home_inline
from locales import t

router = Router()

ABOUT_TEXTS = {
    "en": (
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
        "🌐 Website: unlimitz.space"
    ),
    "ru": (
        "📖 <b>О нас — Unlimitz VPN</b>\n\n"
        "Мы — команда профессионалов, предоставляющих быстрый, безопасный и надёжный VPN по всему миру.\n\n"
        "🎯 <b>Наша миссия</b>\n"
        "Дать каждому свободный и неограниченный доступ к интернету — без цензуры, лимитов и слежки.\n\n"
        "🔐 <b>Почему мы?</b>\n"
        "<blockquote>"
        "⚡ Максимальная скорость\n"
        "🌍 10+ локаций по всему миру\n"
        "🔒 Без логов, полная приватность\n"
        "🛟 Поддержка 24/7\n"
        "💸 Доступные цены"
        "</blockquote>\n\n"
        "📢 Канал: @unlimitzproject\n"
        "🌐 Сайт: unlimitz.space"
    ),
    "uk": (
        "📖 <b>Про нас — Unlimitz VPN</b>\n\n"
        "Ми — команда професіоналів, що надає швидкий, безпечний та надійний VPN по всьому світу.\n\n"
        "🎯 <b>Наша місія</b>\n"
        "Дати кожному вільний та необмежений доступ до інтернету — без цензури, лімітів та стеження.\n\n"
        "🔐 <b>Чому ми?</b>\n"
        "<blockquote>"
        "⚡ Максимальна швидкість\n"
        "🌍 10+ локацій по всьому світу\n"
        "🔒 Без логів, повна приватність\n"
        "🛟 Підтримка 24/7\n"
        "💸 Доступні ціни"
        "</blockquote>\n\n"
        "📢 Канал: @unlimitzproject\n"
        "🌐 Сайт: unlimitz.space"
    ),
}


@router.callback_query(F.data == "about_us")
async def about_us_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        ABOUT_TEXTS.get(lang, ABOUT_TEXTS["en"]),
        reply_markup=back_home_inline(lang)
    )
    await call.answer()