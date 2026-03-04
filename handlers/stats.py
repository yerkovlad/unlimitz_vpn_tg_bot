from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from db.database import SessionFactory
from db.crud import get_bot_stats, get_referral_stats, get_user_ref_percent, set_user_ref_percent
from db.models import User, Subscription, PlanPrice
from filters.admin import IsAdmin

router = Router()


class StatsState(StatesGroup):
    waiting_user = State()
    change_user_percent = State()


def stats_period_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="📅 Day", callback_data="stats:day"),
        InlineKeyboardButton(text="📅 Week", callback_data="stats:week"),
        InlineKeyboardButton(text="📅 Month", callback_data="stats:month"),
        InlineKeyboardButton(text="📅 All time", callback_data="stats:all"),
        InlineKeyboardButton(text="👤 User Stats", callback_data="stats_user_select"),
        InlineKeyboardButton(text="< Back", callback_data="admin_panel")
    )
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


async def show_user_stats(event, user_id: int):
    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        stats = await get_referral_stats(session, user_id)
        percent = await get_user_ref_percent(session, user_id)

        subs_result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subs = subs_result.scalars().all()

        revenue = 0.0
        for sub in subs:
            price_result = await session.execute(
                select(PlanPrice).where(PlanPrice.location_code == sub.geo)
            )
            p = price_result.scalars().first()
            if p:
                revenue += p.price

    username = f"@{user.username}" if user.username else f"id:{user.id}"

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💲 Change Ref %", callback_data=f"change_ref_percent:{user_id}"),
        InlineKeyboardButton(text="< Back", callback_data="admin_stats")
    )
    builder.adjust(2)

    text = (
        f"👤 <b>User: {username}</b>\n\n"
        f"💰 Balance: <code>{user.balance:.2f}$</code>\n"
        f"🛒 Total purchases: <b>{len(subs)}</b>\n"
        f"💲 Revenue from user: <b>{revenue:.2f}$</b>\n\n"
        f"<b>Referral stats:</b>\n"
        f"👥 Invited: <b>{stats['total_refs']}</b>\n"
        f"💲 Ref earned: <b>{stats['total_earned']:.2f}$</b>\n"
        f"📊 Ref percent: <b>{percent}%</b>"
    )

    if isinstance(event, Message):
        await event.answer(text, reply_markup=builder.as_markup())
    else:
        await event.message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(IsAdmin(), F.data == "admin_stats")
async def admin_stats_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("📊 <b>Statistics:</b>", reply_markup=stats_period_inline())
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("stats:"))
async def stats_period_callback(call: CallbackQuery):
    period = call.data.split(":")[1]

    async with SessionFactory() as session:
        s = await get_bot_stats(session, period)

    period_labels = {"day": "Today", "week": "This week", "month": "This month", "all": "All time"}

    await call.message.delete()
    await call.message.answer(
        f"📊 <b>Stats — {period_labels[period]}</b>\n\n"
        f"👥 Total users: <b>{s['total_users']}</b>\n"
        f"🛒 New subscriptions: <b>{s['new_subs']}</b>\n"
        f"💲 Revenue: <b>{s['revenue']:.2f}$</b>\n"
        f"🔗 Referrals: <b>{s['total_refs']}</b>",
        reply_markup=stats_period_inline()
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data == "stats_user_select")
async def stats_user_select(call: CallbackQuery, state: FSMContext):
    await call.message.answer("🔍 Enter user ID or @username:")
    await state.set_state(StatsState.waiting_user)
    await call.answer()


@router.message(IsAdmin(), StatsState.waiting_user)
async def process_stats_user(message: Message, state: FSMContext):
    query = message.text.strip().lstrip("@")
    await state.clear()

    async with SessionFactory() as session:
        if query.isdigit():
            user = await session.get(User, int(query))
        else:
            result = await session.execute(select(User).where(User.username == query))
            user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ User not found.")
        return

    await show_user_stats(message, user.id)


@router.callback_query(IsAdmin(), F.data.startswith("change_ref_percent:"))
async def change_ref_percent_callback(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await call.message.answer("💲 Enter new referral percent (e.g. 25):")
    await state.set_state(StatsState.change_user_percent)
    await call.answer()


@router.message(IsAdmin(), StatsState.change_user_percent)
async def process_change_ref_percent(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid percent. Enter a number:")
        return

    percent = float(message.text)
    if percent < 0 or percent > 100:
        await message.answer("❌ Percent must be between 0 and 100:")
        return

    data = await state.get_data()
    user_id = data["user_id"]
    await state.clear()

    async with SessionFactory() as session:
        await set_user_ref_percent(session, user_id, percent)

    await message.answer(f"✅ Referral percent updated to {percent}%")
    await show_user_stats(message, user_id)