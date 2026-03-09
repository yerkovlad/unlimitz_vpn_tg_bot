from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import SessionFactory
from db.crud import get_referral_stats, get_or_create_user, get_user_ref_percent, get_user_lang
from db.models import User
from keyboards.inline import back_home_inline
from locales import t

router = Router()


def earn_inline(ref_link: str, ref_balance: float, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔗 Share Link", url=f"https://t.me/share/url?url={ref_link}"),
    )
    if ref_balance > 0:
        builder.add(
            InlineKeyboardButton(text=t("btn_transfer", lang), callback_data="ref_transfer"),
        )
    builder.add(
        InlineKeyboardButton(text=t("btn_withdraw", lang), callback_data="ref_withdraw"),
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home")
    )
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(F.data == "earn")
async def earn_callback(call: CallbackQuery):
    bot_username = (await call.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{call.from_user.id}"

    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
        stats = await get_referral_stats(session, call.from_user.id)
        user = await session.get(User, call.from_user.id)
        ref_balance = user.ref_balance if user else 0.0
        percent = await get_user_ref_percent(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        t("earn", lang,
          link=ref_link,
          refs=stats['total_refs'],
          earned=f"{stats['total_earned']:.2f}",
          ref_balance=f"{ref_balance:.2f}",
          percent=percent),
        reply_markup=earn_inline(ref_link, ref_balance, lang)
    )
    await call.answer()


@router.callback_query(F.data == "ref_transfer")
async def ref_transfer_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
        user = await session.get(User, call.from_user.id)
        if not user or user.ref_balance <= 0:
            await call.answer("❌ No referral balance to transfer.", show_alert=True)
            return

        amount = user.ref_balance
        user.balance += amount
        user.ref_balance = 0
        await session.commit()

    await call.answer(
        t("ref_transfer_success", lang, amount=f"{amount:.2f}"),
        show_alert=True
    )

    bot_username = (await call.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{call.from_user.id}"

    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
        stats = await get_referral_stats(session, call.from_user.id)
        user = await session.get(User, call.from_user.id)
        percent = await get_user_ref_percent(session, call.from_user.id)

    await call.message.delete()
    await call.message.answer(
        t("earn", lang,
          link=ref_link,
          refs=stats['total_refs'],
          earned=f"{stats['total_earned']:.2f}",
          ref_balance=f"{user.ref_balance:.2f}",
          percent=percent),
        reply_markup=earn_inline(ref_link, user.ref_balance, lang)
    )


@router.callback_query(F.data == "ref_withdraw")
async def ref_withdraw_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    await call.answer(
        t("ref_withdraw_info", lang),
        show_alert=True
    )