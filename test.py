import asyncio
from sqlalchemy import select

from db.models import Plan, Location, PlanPrice
from db.database import init_db, SessionFactory
from db.crud import get_or_create_user, add_admin, get_price

LOCATIONS = [
    {"name": "🇩🇪 Germany", "code": "de"},
    {"name": "🇳🇱 Netherlands", "code": "nl"},
    {"name": "🇺🇸 USA", "code": "us"},
    {"name": "🇵🇱 Poland", "code": "pl"},
    {"name": "🇹🇷 Turkey", "code": "tr"},
    {"name": "🇫🇮 Finland", "code": "fi"},
    {"name": "🇸🇪 Sweden", "code": "se"},
    {"name": "🇯🇵 Japan", "code": "jp"},
    {"name": "🇰🇿 Kazakhstan", "code": "kz"},
    {"name": "🇮🇳 India", "code": "in"},
]


async def main():
    await init_db()

    async with SessionFactory() as session:
        # Юзер и админ
        user = await get_or_create_user(session, user_id=8093445765, username="unlimitz")
        print(f"User: {user}")

        admin = await add_admin(session, admin_id=8093445765, username="unlimitz")
        print(f"Admin: {admin}")

        # Планы
        for months, price in [(1, 5.0), (3, 13.0), (6, 24.0), (12, 45.0)]:
            existing = await session.execute(select(Plan).where(Plan.duration_months == months))
            if not existing.scalar_one_or_none():
                session.add(Plan(duration_months=months, price=price))
        await session.commit()
        print("Plans created")

        # Локации
        for loc in LOCATIONS:
            existing = await session.get(Location, loc["code"])
            if not existing:
                session.add(Location(code=loc["code"], name=loc["name"]))
        await session.commit()
        print("Locations created")

        # Цены для каждой локации + план
        plans_result = await session.execute(select(Plan))
        plans = plans_result.scalars().all()

        locs_result = await session.execute(select(Location))
        locs = locs_result.scalars().all()

        for plan in plans:
            for loc in locs:
                existing = await get_price(session, plan.id, loc.code)
                if not existing:
                    session.add(PlanPrice(plan_id=plan.id, location_code=loc.code, price=plan.price))

        await session.commit()
        print("Prices created")


asyncio.run(main())