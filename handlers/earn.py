from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import SessionFactory
from db.crud import get_referral_stats, get_or_create_user, get_user_ref_percent
from db.models import User
from keyboards.inline import back_home_inline

router = Router()


def earn_inline(ref_link: str, ref_balance: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔗 Share Link", url=f"https://t.me/share/url?url={ref_link}"),
    )
    if ref_balance > 0:
        builder.add(
            InlineKeyboardButton(text="💸 Transfer to Balance", callback_data="ref_transfer"),
        )
    builder.add(
        InlineKeyboardButton(text="💰 Withdraw", callback_data="ref_withdraw"),
        InlineKeyboardButton(text="🏠 Home", callback_data="back_home")
    )
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "earn")
async def earn_callback(call: CallbackQuery):
    bot_username = (await call.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{call.from_user.id}"

    async with SessionFactory() as session:
        stats = await get_referral_stats(session, call.from_user.id)
        user = await session.get(User, call.from_user.id)
        ref_balance = user.ref_balance if user else 0.0
        percent = await get_user_ref_percent(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        f"💰 <b>Earn with Unlimitz</b>\n\n"
        f"Invite friends and earn <b>{percent}%</b> from every purchase they make.\n\n"
        f"🔗 <b>Your referral link:</b>\n<code>{ref_link}</code>\n\n"
        f"👥 People invited: <b>{stats['total_refs']}</b>\n"
        f"💲 Total earned: <b>{stats['total_earned']:.2f}$</b>\n"
        f"💵 Referral balance: <b>{ref_balance:.2f}$</b>",
        reply_markup=earn_inline(ref_link, ref_balance)
    )
    await call.answer()


@router.callback_query(F.data == "ref_transfer")
async def ref_transfer_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        user = await session.get(User, call.from_user.id)
        if not user or user.ref_balance <= 0:
            await call.answer("❌ No referral balance to transfer.", show_alert=True)
            return

        amount = user.ref_balance
        user.balance += amount
        user.ref_balance = 0
        await session.commit()

    await call.answer(
        f"✅ {amount:.2f}$ transferred to main balance.\n\n"
        f"⚠️ Note: main balance cannot be withdrawn, only used for purchases.",
        show_alert=True
    )

    # Обновить страницу earn
    bot_username = (await call.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{call.from_user.id}"

    async with SessionFactory() as session:
        stats = await get_referral_stats(session, call.from_user.id)
        user = await session.get(User, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        f"💰 <b>Earn with Unlimitz</b>\n\n"
        f"Invite friends and earn from every purchase they make.\n\n"
        f"🔗 <b>Your referral link:</b>\n<code>{ref_link}</code>\n\n"
        f"👥 People invited: <b>{stats['total_refs']}</b>\n"
        f"💲 Total earned: <b>{stats['total_earned']:.2f}$</b>\n"
        f"💵 Referral balance: <b>{user.ref_balance:.2f}$</b>",
        reply_markup=earn_inline(ref_link, user.ref_balance)
    )


@router.callback_query(F.data == "ref_withdraw")
async def ref_withdraw_callback(call: CallbackQuery):
    await call.answer(
        "⚠️ Automatic withdrawal is currently unavailable.\n\n"
        "Please contact our manager: @unlimitz",
        show_alert=True
    )