import time
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import SessionFactory
from db.crud import activate_promo, get_available_server, increment_server_users
from db.models import Subscription, PromoCode
from vless.api import generate_vless_link
from keyboards.inline import back_home_inline

router = Router()


class PromoState(StatesGroup):
    waiting_code = State()


@router.callback_query(F.data == "promo")
async def promo_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(
        "🎁 <b>Promo Code</b>\n\n"
        "Enter your promo code:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Home", callback_data="back_home")]
        ])
    )
    await state.set_state(PromoState.waiting_code)
    await call.answer()


@router.message(PromoState.waiting_code)
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    await state.clear()

    async with SessionFactory() as session:
        result = await session.execute(
            select(PromoCode)
            .where(PromoCode.code == code)
            .options(selectinload(PromoCode.plan), selectinload(PromoCode.location))
        )
        promo = result.scalar_one_or_none()

        if not promo:
            await message.answer("❌ <b>Invalid promo code.</b>", reply_markup=back_home_inline())
            return

        if not promo.is_active:
            await message.answer("❌ <b>This promo code is no longer active.</b>", reply_markup=back_home_inline())
            return

        if promo.expires_at and promo.expires_at < datetime.utcnow():
            await message.answer("❌ <b>This promo code has expired.</b>", reply_markup=back_home_inline())
            return

        if promo.used_count >= promo.max_uses:
            await message.answer("❌ <b>This promo code has reached its usage limit.</b>", reply_markup=back_home_inline())
            return

        server = await get_available_server(session, promo.location_code)
        if not server:
            await message.answer("❌ <b>No available servers for this location.</b>", reply_markup=back_home_inline())
            return

        activated = await activate_promo(session, promo, message.from_user.id)
        if not activated:
            await message.answer("❌ <b>You have already used this promo code.</b>", reply_markup=back_home_inline())
            return

        if promo.duration_days:
            days = promo.duration_days
            traffic_gb = max(10, promo.duration_days * 3)
            plan_id_str = "free"
            duration_label = f"{days} day(s)"
        else:
            plan = promo.plan
            days = plan.duration_months * 30
            traffic_gb = plan.duration_months * 100
            plan_id_str = str(plan.id)
            duration_label = f"{plan.duration_months} month(s)"

        location_name = promo.location.name
        name = f"user_{message.from_user.id}_{plan_id_str}_{promo.location_code}_{int(time.time())}"

        vless_result = await generate_vless_link(server, name, days=days, traffic_gb=traffic_gb)
        if not vless_result:
            await message.answer("❌ <b>Failed to create VPN config. Please contact support.</b>", reply_markup=back_home_inline())
            return

        vless_link, client_uuid = vless_result

        duration_start = datetime.utcnow()
        duration_end = duration_start + timedelta(days=days)

        sub = Subscription(
            user_id=message.from_user.id,
            server_id=server.id,
            profile_username=name,
            profile_id=name,
            client_uuid=client_uuid,
            duration_start=duration_start,
            duration_end=duration_end,
            geo=promo.location_code,
            vless_link=vless_link
        )
        session.add(sub)
        await increment_server_users(session, server.id)
        await session.commit()

    await message.answer(
        f"✅ <b>Promo code activated!</b>\n\n"
        f"🌍 Location: {location_name}\n"
        f"⏳ Duration: {duration_label}\n"
        f"📊 Traffic: {traffic_gb} GB\n\n"
        f"🔗 <b>Your config:</b>\n<code>{vless_link}</code>",
        reply_markup=back_home_inline()
    )
