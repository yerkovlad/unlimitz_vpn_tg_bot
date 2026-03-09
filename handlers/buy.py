from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
import time
from sqlalchemy import select as sa_select

from db.database import SessionFactory
from db.crud import get_all_locations, get_available_server, get_price, get_or_create_user, get_active_plans, add_referral_earning, get_user_lang
from db.models import Subscription, Plan, Location, Referral
from vless.api import generate_vless_link
from keyboards.inline import back_home_inline
from locales import t

router = Router()

LOCATIONS_PER_PAGE = 4


async def get_active_locations():
    async with SessionFactory() as session:
        locs = await get_all_locations(session)
        return [l for l in locs if l.is_active]


def locations_inline(locations, page: int, lang: str = "en") -> InlineKeyboardMarkup:
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
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


async def plans_inline_with_prices(plans, location_code: str, lang: str = "en") -> InlineKeyboardMarkup:
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
    builder.row(InlineKeyboardButton(text=t("btn_back_short", lang), callback_data="buy_vpn_page:0"))
    return builder.as_markup()


def confirm_purchase_inline(location_code: str, plan_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_back_short", lang), callback_data=f"select_location:{location_code}"),
        InlineKeyboardButton(text=t("btn_confirm", lang), callback_data=f"confirm_purchase:{location_code}:{plan_id}")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(F.data == "buy_vpn")
async def buy_vpn_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    locations = await get_active_locations()
    await call.message.delete()
    await call.message.answer(
        t("select_location", lang),
        reply_markup=locations_inline(locations, 0, lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy_vpn_page:"))
async def buy_vpn_page_callback(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    locations = await get_active_locations()
    await call.message.delete()
    await call.message.answer(
        t("select_location", lang),
        reply_markup=locations_inline(locations, page, lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("select_location:"))
async def select_location_callback(call: CallbackQuery):
    code = call.data.split(":")[1]

    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
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
        t("select_plan", lang, location=location.name),
        reply_markup=await plans_inline_with_prices(plans, code, lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("select_plan:"))
async def select_plan_callback(call: CallbackQuery):
    _, location_code, plan_id = call.data.split(":")

    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
        plan = await session.get(Plan, int(plan_id))
        location = await session.get(Location, location_code)
        price_obj = await get_price(session, plan.id, location_code)
        price = price_obj.price if price_obj else plan.price

    months = plan.duration_months
    await call.message.delete()
    await call.message.answer(
        t("buy_confirm", lang,
          location=location.name,
          months=months,
          traffic=months * 100,
          price=price),
        reply_markup=confirm_purchase_inline(location_code, plan.id, lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("confirm_purchase:"))
async def confirm_purchase_callback(call: CallbackQuery):
    _, location_code, plan_id = call.data.split(":")

    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
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
                t("not_enough_balance", lang, balance=round(user.balance, 2)),
                show_alert=True
            )
            return

        user.balance -= price

        days = plan.duration_months * 30
        now = datetime.utcnow()
        name = f"user_{call.from_user.id}_{plan.id}_{location_code}_{int(time.time())}"
        traffic_gb = plan.duration_months * 100

        result = await generate_vless_link(server, name, days=days, traffic_gb=traffic_gb)
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

        ref_result = await session.execute(
            sa_select(Referral).where(Referral.referred_id == call.from_user.id)
        )
        ref = ref_result.scalar_one_or_none()
        if ref:
            earning = await add_referral_earning(session, ref.referrer_id, call.from_user.id, price)
            try:
                await call.bot.send_message(
                    ref.referrer_id,
                    f"💰 <b>Referral bonus!</b>\n"
                    f"Your friend made a purchase.\n"
                    f"You earned: <code>{earning:.2f}$</code>"
                )
            except Exception:
                pass

    await call.message.delete()
    await call.message.answer(
        t("purchase_success", lang,
          location=location_code.upper(),
          date=(now + timedelta(days=days)).strftime("%d.%m.%Y"),
          traffic=traffic_gb,
          link=link),
        reply_markup=back_home_inline(lang)
    )
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(call: CallbackQuery):
    await call.answer()