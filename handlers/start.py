from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.inline import menu_inline, back_home_inline
from db import get_or_create_user
from db.database import SessionFactory
from db.crud import create_referral, get_all_locations, get_user_lang
from locales import t
from handlers.language import lang_inline

router = Router()


async def get_welcome_text(lang: str = "en") -> str:
    async with SessionFactory() as session:
        locations = await get_all_locations(session)
        active = [l for l in locations if l.is_active]

    locations_str = ", ".join(l.name for l in active) if active else "Coming soon"
    return t("welcome", lang, locations=locations_str)


@router.message(CommandStart())
async def cmd_start(message: Message):
    async with SessionFactory() as session:
        user = await get_or_create_user(
            session,
            user_id=message.from_user.id,
            username=message.from_user.username
        )
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != message.from_user.id:
                await create_referral(session, referrer_id, message.from_user.id)
        lang = user.lang or "en"
        is_new = user.lang is None

    if is_new:
        await message.answer(
            "🌍 Choose language / Выберите язык / Оберіть мову:",
            reply_markup=lang_inline()
        )
        return

    await message.answer(await get_welcome_text(lang), reply_markup=menu_inline(lang))


@router.callback_query(F.data == "back_home")
async def back_home_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(await get_welcome_text(lang), reply_markup=menu_inline(lang))
    await call.answer()


@router.callback_query(F.data == "close")
async def callback_close(call: CallbackQuery):
    await call.message.delete()
    await call.answer()


@router.callback_query(F.data == "terms")
async def terms_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    texts = {
        "en": (
            "📄 <b>User Agreement — Unlimitz VPN</b>\n\n"
            "<b>⚠️ PUBLIC OFFER</b>\n"
            "By using the service you automatically accept these terms.\n\n"
            "<b>1. General</b>\n"
            "The Service provides technical access to remote servers (Private Proxy) for personal, educational, or corporate purposes.\n\n"
            "<b>2. Prohibited</b>\n"
            "• Illegal activities\n• DDoS, spam, phishing, carding\n"
            "• Distribution of malware\n• Illegal content (CSAM, terrorism)\n"
            "• Torrent\n• Transferring credentials to third parties\n\n"
            "<b>3. Liability</b>\n"
            "All legal responsibility for your actions lies solely with you. The Administration follows a strict no-log policy.\n\n"
            "<b>4. Disclaimer</b>\n"
            "The Administration is not liable for damages caused by DPI/state blocking (Force Majeure).\n\n"
            "Full agreement: unlimitz.space/terms"
        ),
        "ru": (
            "📄 <b>Пользовательское соглашение — Unlimitz VPN</b>\n\n"
            "<b>⚠️ ПУБЛИЧНАЯ ОФЕРТА</b>\n"
            "Используя сервис, вы автоматически принимаете данные условия.\n\n"
            "<b>1. Общее</b>\n"
            "Сервис предоставляет технический доступ к удалённым серверам для личных, образовательных или корпоративных целей.\n\n"
            "<b>2. Запрещено</b>\n"
            "• Незаконная деятельность\n• DDoS, спам, фишинг, кардинг\n"
            "• Распространение вредоносного ПО\n• Незаконный контент\n"
            "• Торрент\n• Передача данных третьим лицам\n\n"
            "<b>3. Ответственность</b>\n"
            "Вся юридическая ответственность лежит на вас. Администрация придерживается политики no-log.\n\n"
            "<b>4. Отказ от ответственности</b>\n"
            "Администрация не несёт ответственности за блокировки DPI (форс-мажор).\n\n"
            "Полное соглашение: unlimitz.space/terms"
        ),
        "uk": (
            "📄 <b>Угода користувача — Unlimitz VPN</b>\n\n"
            "<b>⚠️ ПУБЛІЧНА ОФЕРТА</b>\n"
            "Використовуючи сервіс, ви автоматично приймаєте ці умови.\n\n"
            "<b>1. Загальне</b>\n"
            "Сервіс надає технічний доступ до віддалених серверів для особистих, освітніх або корпоративних цілей.\n\n"
            "<b>2. Заборонено</b>\n"
            "• Незаконна діяльність\n• DDoS, спам, фішинг, кардинг\n"
            "• Розповсюдження шкідливого ПЗ\n• Незаконний контент\n"
            "• Торрент\n• Передача даних третім особам\n\n"
            "<b>3. Відповідальність</b>\n"
            "Вся юридична відповідальність лежить на вас. Адміністрація дотримується політики no-log.\n\n"
            "<b>4. Відмова від відповідальності</b>\n"
            "Адміністрація не несе відповідальності за блокування DPI (форс-мажор).\n\n"
            "Повна угода: unlimitz.space/terms"
        ),
    }

    await call.message.delete()
    await call.message.answer(texts.get(lang, texts["en"]), reply_markup=back_home_inline(lang))
    await call.answer()


def info_inline(lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📄 Privacy Policy", url="https://telegra.ph/Privacy-Policy--Unlimitz-VPN-03-06"),
        InlineKeyboardButton(text="📋 Terms of Service", url="https://telegra.ph/Terms-of-Service--Unlimitz-VPN-03-06"),
    )
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


@router.callback_query(F.data == "info")
async def info_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        t("info", lang),
        reply_markup=info_inline(lang)
    )
    await call.answer()