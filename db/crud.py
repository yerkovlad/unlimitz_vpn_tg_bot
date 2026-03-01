from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Admin, User, Subscription, Plan, Location, PlanPrice, Server


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
    result = await session.execute(select(Location).order_by(Location.name))
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
                     location_code: str, inbound_id: int = 1, max_users: int = 40) -> Server:
    server = Server(
        name=name, ip=ip, port=port,
        location_code=location_code,
        inbound_id=inbound_id,
        max_users=max_users
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