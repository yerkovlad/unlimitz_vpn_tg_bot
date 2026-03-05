from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from keyboards.reply import main_menu
from keyboards.inline import *

from db import get_or_create_user
from db.database import SessionFactory
from db.crud import create_referral

router = Router()

async def get_welcome_text() -> str:
    async with SessionFactory() as session:
        from db.crud import get_all_locations
        locations = await get_all_locations(session)
        active = [l for l in locations if l.is_active]

    locations_str = ", ".join(l.name for l in active) if active else "Coming soon"

    return (
        "🚀 <b>Unlimitz VPN — Fast & Secure Access</b>\n\n"
        "🌍 <b>Locations:</b>\n"
        f"<blockquote>{locations_str}</blockquote>\n\n"
        "💎 <b>Benefits:</b>\n"
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

    await message.answer(await get_welcome_text(), reply_markup=menu_inline())


@router.callback_query(F.data == "back_home")
async def back_home_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(await get_welcome_text(), reply_markup=menu_inline())
    await call.answer()


@router.callback_query(F.data == "close")
async def callback_close(call: CallbackQuery):
    await call.message.delete()
    await call.answer()

@router.callback_query(F.data == "terms")
async def terms_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "📄 <b>User Agreement — Unlimitz VPN</b>\n\n"
        "<b>⚠️ PUBLIC OFFER</b>\n"
        "By using the service you automatically accept these terms.\n\n"
        "<b>1. General</b>\n"
        "The Service provides technical access to remote servers (Private Proxy) for personal, educational, or corporate purposes.\n\n"
        "<b>2. Prohibited</b>\n"
        "• Illegal activities\n"
        "• DDoS, spam, phishing, carding\n"
        "• Distribution of malware\n"
        "• Illegal content (CSAM, terrorism)\n"
        "• Torrent\n"
        "• Transferring credentials to third parties\n\n"
        "<b>3. Liability</b>\n"
        "All legal responsibility for your actions lies solely with you. The Administration follows a strict no-log policy.\n\n"
        "<b>4. Disclaimer</b>\n"
        "The Administration is not liable for damages or service interruptions caused by DPI/state blocking (Force Majeure). No refunds in such cases.\n\n"
        "Full agreement: unlimitz.space/terms",
        reply_markup=back_home_inline()
    )
    await call.answer()