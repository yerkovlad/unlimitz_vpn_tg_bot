from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import time

from db.database import SessionFactory
from db.crud import get_all_locations, get_available_server, get_price, get_or_create_user, get_active_plans
from db.models import Subscription, Plan, Location
from vless.api import generate_vless_link
from keyboards.inline import back_home_inline

router = Router()

LOCATIONS_PER_PAGE = 4


async def get_active_locations():
    async with SessionFactory() as session:
        locs = await get_all_locations(session)
        return [l for l in locs if l.is_active]


def locations_inline(locations, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    total = len(locations)
    start = page * LOCATIONS_PER_PAGE
    end = min(start + LOCATIONS_PER_PAGE, total)

    for loc in locations[start:end]:
        builder.add(InlineKeyboardButton(
            text=loc.name,
            callback_data=f"select_location:{loc.code}"
        ))
    builder.adjust(2)

    total_pages = max(1, -(-total // LOCATIONS_PER_PAGE))
    prev_cb = f"buy_vpn_page:{page - 1}" if page > 0 else "noop"
    next_cb = f"buy_vpn_page:{page + 1}" if page + 1 < total_pages else "noop"

    builder.row(
        InlineKeyboardButton(text="<", callback_data=prev_cb),
        InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="noop"),
        InlineKeyboardButton(text=">", callback_data=next_cb),
    )
    builder.row(InlineKeyboardButton(text="Home", callback_data="back_home"))
    return builder.as_markup()


async def plans_inline_with_prices(plans, location_code: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    async with SessionFactory() as session:
        for plan in plans:
            price_obj = await get_price(session, plan.id, location_code)
            price = price_obj.price if price_obj else plan.price
            builder.add(InlineKeyboardButton(
                text=f"{plan.duration_months} month{'s' if plan.duration_months > 1 else ''} — {price}$",
                callback_data=f"select_plan:{location_code}:{plan.id}"
            ))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="< Back", callback_data="buy_vpn_page:0"))
    return builder.as_markup()


def confirm_purchase_inline(location_code: str, plan_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="< Back", callback_data=f"select_location:{location_code}"),
        InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_purchase:{location_code}:{plan_id}")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(F.data == "buy_vpn")
async def buy_vpn_callback(call: CallbackQuery):
    locations = await get_active_locations()
    await call.message.delete()
    await call.message.answer("🌍 <b>Select a location:</b>", reply_markup=locations_inline(locations, 0))
    await call.answer()


@router.callback_query(F.data.startswith("buy_vpn_page:"))
async def buy_vpn_page_callback(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    locations = await get_active_locations()
    await call.message.delete()
    await call.message.answer("🌍 <b>Select a location:</b>", reply_markup=locations_inline(locations, page))
    await call.answer()


@router.callback_query(F.data.startswith("select_location:"))
async def select_location_callback(call: CallbackQuery):
    code = call.data.split(":")[1]

    async with SessionFactory() as session:
        location = await session.get(Location, code)
        server = await get_available_server(session, code)

        if not server:
            await call.answer("😔 Sorry, this location is currently unavailable.", show_alert=True)
            return

        plans = await get_active_plans(session)

    if not plans:
        await call.answer("No plans available", show_alert=True)
        return

    await call.message.delete()
    await call.message.answer(
        f"📅 <b>Select a plan for {location.name}:</b>",
        reply_markup=await plans_inline_with_prices(plans, code)
    )
    await call.answer()


@router.callback_query(F.data.startswith("select_plan:"))
async def select_plan_callback(call: CallbackQuery):
    _, location_code, plan_id = call.data.split(":")

    async with SessionFactory() as session:
        plan = await session.get(Plan, int(plan_id))
        location = await session.get(Location, location_code)
        price_obj = await get_price(session, plan.id, location_code)
        price = price_obj.price if price_obj else plan.price

    months = plan.duration_months
    await call.message.delete()
    await call.message.answer(
        f"🛒 <b>Order Summary:</b>\n\n"
        f"🌍 Location: {location.name}\n"
        f"📅 Duration: {months} month{'s' if months > 1 else ''}\n"
        f"💲 Price: <code>{price}$</code>\n\n"
        "Confirm your purchase?",
        reply_markup=confirm_purchase_inline(location_code, plan.id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm_purchase:"))
async def confirm_purchase_callback(call: CallbackQuery):
    _, location_code, plan_id = call.data.split(":")

    async with SessionFactory() as session:
        server = await get_available_server(session, location_code)
        if not server:
            await call.answer("😔 Sorry, this location is currently unavailable.", show_alert=True)
            return

        plan = await session.get(Plan, int(plan_id))
        price_obj = await get_price(session, plan.id, location_code)
        price = price_obj.price if price_obj else plan.price

        user = await get_or_create_user(session, call.from_user.id, call.from_user.username)
        if user.balance < price:
            await call.answer(
                f"❌ Insufficient balance. Need {price}$, you have {user.balance}$",
                show_alert=True
            )
            return

        user.balance -= price

        days = plan.duration_months * 30
        now = datetime.utcnow()
        name = f"user_{call.from_user.id}_{plan.id}_{location_code}_{int(time.time())}"

        result = await generate_vless_link(server, name, days=days, traffic_gb=100)
        if not result:
            user.balance += price
            await session.commit()
            await call.answer("❌ Server error. Please try again.", show_alert=True)
            return

        link, client_uuid = result

        sub = Subscription(
            user_id=call.from_user.id,
            server_id=server.id,
            profile_username=name,
            profile_id=name,
            client_uuid=client_uuid,
            duration_start=now,
            duration_end=now + timedelta(days=days),
            geo=location_code,
            vless_link=link
        )
        session.add(sub)
        server.current_users += 1
        await session.commit()

    await call.message.delete()
    await call.message.answer(
        f"✅ <b>Purchase successful!</b>\n\n"
        f"🌍 Location: {location_code.upper()}\n"
        f"📅 Duration: {plan.duration_months} month{'s' if plan.duration_months > 1 else ''}\n"
        f"💲 Paid: <code>{price}$</code>\n\n"
        f"🔑 <b>Your VPN link:</b>\n<code>{link}</code>",
        reply_markup=back_home_inline()
    )
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(call: CallbackQuery):
    await call.answer()