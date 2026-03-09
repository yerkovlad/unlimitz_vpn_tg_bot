from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime
from sqlalchemy import select

from db.database import SessionFactory
from db.crud import get_user_lang
from db.models import Subscription
from keyboards.inline import back_home_inline
from locales import t

router = Router()

SUBS_PER_PAGE = 1


def sub_detail_inline(sub_id: int, page: int, total: int, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="<", callback_data=f"my_subs:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total}", callback_data="noop"))
    if page + 1 < total:
        nav.append(InlineKeyboardButton(text=">", callback_data=f"my_subs:{page + 1}"))

    builder.row(*nav)
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


@router.callback_query(F.data == "my_subs")
async def my_subs_callback(call: CallbackQuery):
    await show_sub_page(call, 0)


@router.callback_query(F.data.startswith("my_subs:"))
async def my_subs_page_callback(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    await show_sub_page(call, page)


async def show_sub_page(call: CallbackQuery, page: int):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == call.from_user.id)
            .order_by(Subscription.duration_start.desc())
        )
        subs = result.scalars().all()

    if not subs:
        await call.message.delete()
        await call.message.answer(
            t("no_subs", lang),
            reply_markup=back_home_inline(lang)
        )
        await call.answer()
        return

    total = len(subs)
    sub = subs[page]
    now = datetime.utcnow()

    is_active = sub.duration_end > now
    status = "🟢 Active" if is_active else "🔴 Expired"
    days_left = (sub.duration_end - now).days if is_active else 0

    await call.message.delete()
    await call.message.answer(
        f"📋 <b>{t('subs_list', lang)} {page + 1}/{total}</b>\n\n"
        f"🌍 Location: <b>{sub.geo.upper()}</b>\n"
        f"Status: {status}\n"
        f"📅 Start: {sub.duration_start.strftime('%d.%m.%Y')}\n"
        f"📅 End: {sub.duration_end.strftime('%d.%m.%Y')}\n"
        f"⏳ Days left: {days_left}\n\n"
        f"🔑 <b>VPN Link:</b>\n<code>{sub.vless_link}</code>",
        reply_markup=sub_detail_inline(sub.id, page, total, lang)
    )
    await call.answer()