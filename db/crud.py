from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import *


# --- Admins ---

async def get_admin(session: AsyncSession, admin_id: int) -> Admin | None:
    return await session.get(Admin, admin_id)

async def add_admin(session: AsyncSession, admin_id: int, username: str = None) -> Admin:
    existing = await session.get(Admin, admin_id)
    if existing:
        return existing
    admin = Admin(id=admin_id, username=username)
    session.add(admin)
    await session.commit()
    return admin

async def is_admin(session: AsyncSession, admin_id: int) -> bool:
    return await get_admin(session, admin_id) is not None


# --- Users ---

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)

async def get_or_create_user(session: AsyncSession, user_id: int, username: str = None) -> User:
    user = await get_user(session, user_id)
    if not user:
        user = User(id=user_id, username=username)
        session.add(user)
        await session.commit()
    return user

async def update_balance(session: AsyncSession, user_id: int, amount: float) -> User | None:
    user = await get_user(session, user_id)
    if user:
        user.balance += amount
        await session.commit()
    return user


# --- Subscriptions ---

async def add_subscription(
    session: AsyncSession,
    user_id: int,
    profile_username: str,
    profile_id: str,
    duration_start: datetime,
    duration_end: datetime,
    geo: str,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        profile_username=profile_username,
        profile_id=profile_id,
        duration_start=duration_start,
        duration_end=duration_end,
        geo=geo,
    )
    session.add(sub)
    await session.commit()
    return sub

async def get_user_subscriptions(session: AsyncSession, user_id: int) -> list[Subscription]:
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    return result.scalars().all()

async def get_active_subscriptions(session: AsyncSession, user_id: int) -> list[Subscription]:
    now = datetime.utcnow()
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.duration_end > now
        )
    )
    return result.scalars().all()

async def get_active_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.duration_months)
    )
    return result.scalars().all()

async def get_all_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(select(Plan).order_by(Plan.duration_months))
    return result.scalars().all()

async def update_plan_price(session: AsyncSession, plan_id: int, price: float) -> Plan | None:
    plan = await session.get(Plan, plan_id)
    if plan:
        plan.price = price
        await session.commit()
    return plan

async def toggle_plan(session: AsyncSession, plan_id: int) -> Plan | None:
    plan = await session.get(Plan, plan_id)
    if plan:
        plan.is_active = not plan.is_active
        await session.commit()
    return plan

async def get_all_locations(session: AsyncSession) -> list[Location]:
    result = await session.execute(select(Location).order_by(Location.code))
    return result.scalars().all()

async def toggle_location(session: AsyncSession, code: str) -> Location | None:
    loc = await session.get(Location, code)
    if loc:
        loc.is_active = not loc.is_active
        await session.commit()
    return loc

async def get_price(session: AsyncSession, plan_id: int, location_code: str) -> PlanPrice | None:
    result = await session.execute(
        select(PlanPrice).where(
            PlanPrice.plan_id == plan_id,
            PlanPrice.location_code == location_code
        )
    )
    return result.scalar_one_or_none()

async def set_price(session: AsyncSession, plan_id: int, location_code: str, price: float) -> PlanPrice:
    existing = await get_price(session, plan_id, location_code)
    if existing:
        existing.price = price
    else:
        existing = PlanPrice(plan_id=plan_id, location_code=location_code, price=price)
        session.add(existing)
    await session.commit()
    return existing

async def get_prices_for_location(session: AsyncSession, location_code: str) -> list[PlanPrice]:
    result = await session.execute(
        select(PlanPrice).where(PlanPrice.location_code == location_code)
    )
    return result.scalars().all()

async def get_available_server(session: AsyncSession, location_code: str) -> Server | None:
    result = await session.execute(
        select(Server).where(
            Server.location_code == location_code,
            Server.is_active == True,
            Server.current_users < Server.max_users
        ).order_by(Server.current_users)
    )
    return result.scalars().first()

async def get_all_servers(session: AsyncSession) -> list[Server]:
    result = await session.execute(select(Server).order_by(Server.location_code))
    return result.scalars().all()

async def get_servers_by_location(session: AsyncSession, location_code: str) -> list[Server]:
    result = await session.execute(
        select(Server).where(Server.location_code == location_code)
    )
    return result.scalars().all()

async def add_server(session: AsyncSession, name: str, ip: str, port: int,
                     location_code: str, inbound_id: int = 1, 
                     max_users: int = 40, uri_path: str = "/") -> Server:
    server = Server(
        name=name, ip=ip, port=port,
        location_code=location_code,
        inbound_id=inbound_id,
        max_users=max_users,
        uri_path=uri_path
    )
    session.add(server)
    await session.commit()
    return server

async def increment_server_users(session: AsyncSession, server_id: int):
    server = await session.get(Server, server_id)
    if server:
        server.current_users += 1
        await session.commit()

async def decrement_server_users(session: AsyncSession, server_id: int):
    server = await session.get(Server, server_id)
    if server and server.current_users > 0:
        server.current_users -= 1
        await session.commit()

async def get_subscription(session: AsyncSession, sub_id: int) -> Subscription | None:
    return await session.get(Subscription, sub_id)

async def delete_subscription(session: AsyncSession, sub_id: int):
    sub = await session.get(Subscription, sub_id)
    if sub:
        await session.delete(sub)
        await session.commit()
    return sub

async def get_referral_settings(session: AsyncSession) -> float:
    result = await session.execute(select(ReferralSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ReferralSettings(default_percent=30.0)
        session.add(settings)
        await session.commit()
    return settings.default_percent

async def set_referral_percent(session: AsyncSession, percent: float):
    result = await session.execute(select(ReferralSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ReferralSettings(default_percent=percent)
        session.add(settings)
    else:
        settings.default_percent = percent
    await session.commit()

async def get_user_ref_percent(session: AsyncSession, user_id: int) -> float:
    user = await session.get(User, user_id)
    if user and user.ref_percent is not None:
        return user.ref_percent
    return await get_referral_settings(session)

async def set_user_ref_percent(session: AsyncSession, user_id: int, percent: float):
    user = await session.get(User, user_id)
    if user:
        user.ref_percent = percent
        await session.commit()

async def create_referral(session: AsyncSession, referrer_id: int, referred_id: int):
    existing = await session.execute(
        select(Referral).where(Referral.referred_id == referred_id)
    )
    if not existing.scalar_one_or_none():
        session.add(Referral(referrer_id=referrer_id, referred_id=referred_id))
        await session.commit()

async def add_referral_earning(session: AsyncSession, referrer_id: int, referred_id: int, purchase_amount: float) -> float:
    percent = await get_user_ref_percent(session, referrer_id)
    earning = purchase_amount * percent / 100

    session.add(ReferralEarning(
        referrer_id=referrer_id,
        referred_id=referred_id,
        amount=earning,
        percent=percent
    ))

    referrer = await session.get(User, referrer_id)
    if referrer:
        referrer.ref_balance += earning

    await session.commit()
    return earning

async def get_referral_stats(session: AsyncSession, referrer_id: int) -> dict:
    refs = await session.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id)
    )
    total_refs = refs.scalar() or 0

    earnings = await session.execute(
        select(func.sum(ReferralEarning.amount)).where(ReferralEarning.referrer_id == referrer_id)
    )
    total_earned = earnings.scalar() or 0.0

    return {"total_refs": total_refs, "total_earned": total_earned}

async def get_bot_stats(session: AsyncSession, period: str = "all") -> dict:
    from datetime import timedelta
    now = datetime.utcnow()

    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(weeks=1)
    elif period == "month":
        since = now - timedelta(days=30)
    else:
        since = None

    user_query = select(func.count(User.id))
    sub_query = select(func.count(Subscription.id))
    earning_query = select(func.sum(PlanPrice.price))
    ref_query = select(func.count(Referral.id))

    if since:
        sub_query = sub_query.where(Subscription.duration_start >= since)
        ref_query = ref_query.where(Referral.created_at >= since)
        user_query = user_query.where(User.id.in_(
            select(Subscription.user_id).where(Subscription.duration_start >= since)
        ))

    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    new_subs = (await session.execute(sub_query)).scalar() or 0

    # Считаем доход из подписок
    subs_result = await session.execute(
        select(Subscription).where(Subscription.duration_start >= since) if since
        else select(Subscription)
    )
    subs = subs_result.scalars().all()

    revenue = 0.0
    for sub in subs:
        price_obj = await session.execute(
            select(PlanPrice).where(
                PlanPrice.location_code == sub.geo
            )
        )
        p = price_obj.scalars().first()
        if p:
            revenue += p.price

    total_refs = (await session.execute(ref_query)).scalar() or 0

    return {
        "total_users": total_users,
        "new_subs": new_subs,
        "revenue": revenue,
        "total_refs": total_refs
    }


from db.models import PromoCode, PromoActivation

async def get_promo(session: AsyncSession, code: str) -> PromoCode | None:
    result = await session.execute(
        select(PromoCode).where(PromoCode.code == code.upper())
    )
    return result.scalar_one_or_none()


async def activate_promo(session: AsyncSession, promo: PromoCode, user_id: int) -> bool:
    existing = await session.execute(
        select(PromoActivation).where(
            PromoActivation.promo_id == promo.id,
            PromoActivation.user_id == user_id
        )
    )
    if existing.scalar_one_or_none():
        return False
    promo.used_count += 1
    session.add(PromoActivation(promo_id=promo.id, user_id=user_id))
    await session.commit()
    return True


async def get_all_promos(session: AsyncSession) -> list[PromoCode]:
    result = await session.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))
    return result.scalars().all()


async def create_promo(session: AsyncSession, code: str, plan_id: int | None,
                       location_code: str, max_uses: int,
                       expires_at=None, duration_days: int | None = None) -> PromoCode:
    promo = PromoCode(
        code=code.upper(),
        plan_id=plan_id,
        location_code=location_code,
        max_uses=max_uses,
        expires_at=expires_at,
        duration_days=duration_days
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def delete_promo(session: AsyncSession, promo_id: int):
    promo = await session.get(PromoCode, promo_id)
    if promo:
        await session.delete(promo)
        await session.commit()


async def toggle_promo(session: AsyncSession, promo_id: int):
    promo = await session.get(PromoCode, promo_id)
    if promo:
        promo.is_active = not promo.is_active
        await session.commit()
