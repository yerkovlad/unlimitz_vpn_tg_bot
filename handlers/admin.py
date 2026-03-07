from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from config import ADMIN_ID
from filters.admin import IsAdmin
from keyboards.inline import admin_panel_inline, user_manage_inline, back_home_inline
from db.database import SessionFactory
from db.models import User, Plan, Location
from db.crud import get_all_plans, update_plan_price, toggle_plan, get_all_locations, toggle_location

from db.crud import get_all_servers, get_servers_by_location, add_server
from db.crud import get_all_promos, create_promo, delete_promo, toggle_promo, get_promo
from vless.api import check_server_alive
from db.crud import get_subscription, delete_subscription, get_user_subscriptions
from db.models import Server
from vless.api import delete_vless_client

router = Router()

USERS_PER_PAGE = 4
SERVERS_PER_PAGE = 5


class AdminState(StatesGroup):
    search_user = State()
    change_balance = State()
    change_plan_price = State()
    change_location_price = State()
    add_server_name = State()
    add_server_ip = State()
    add_server_port = State()
    add_server_location = State()
    add_server_inbound = State()
    change_ref_balance = State()
    add_location_code = State()
    add_location_name = State()
    add_server_uri = State()
    edit_max_users = State()
    broadcast_text = State()
    promo_code = State()
    promo_plan = State()
    promo_location = State()
    promo_uses = State()
    promo_expires = State()


async def get_users_page(page: int):
    async with SessionFactory() as session:
        result = await session.execute(select(User))
        all_users = result.scalars().all()
    return all_users, page


def users_list_inline(users, page: int, total: int) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    builder = InlineKeyboardBuilder()
    for user in users:
        username = f"@{user.username}" if user.username else f"id:{user.id}"
        builder.add(InlineKeyboardButton(
            text=f"👤 {username} | 💲{user.balance}$",
            callback_data=f"user_info:{user.id}"
        ))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"users_list:{page - 1}"))
    if (page + 1) * USERS_PER_PAGE < total:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"users_list:{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel"))
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("admin"))
@router.message(IsAdmin(), Command("admin"))
async def cmd_admin(message: Message):
    await message.answer(
        "🔧 <b>Admin Panel</b>\n\n"
        f"Your ID: <code>{ADMIN_ID}</code>",
        reply_markup=admin_panel_inline()
    )


@router.callback_query(IsAdmin(), F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "🔧 <b>Admin Panel</b>",
        reply_markup=admin_panel_inline()
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("users_list:"))
async def users_list_callback(call: CallbackQuery):
    page = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        result = await session.execute(select(User))
        all_users = result.scalars().all()

    total = len(all_users)
    users = all_users[page * USERS_PER_PAGE:(page + 1) * USERS_PER_PAGE]

    await call.message.delete()
    await call.message.answer(
        f"👥 <b>Users</b> (page {page + 1}/{max(1, -(-total // USERS_PER_PAGE))}):",
        reply_markup=users_list_inline(users, page, total)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("user_info:"))
async def user_info_callback(call: CallbackQuery):
    user_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        from db.crud import get_user_ref_percent
        percent = await get_user_ref_percent(session, user_id)

    if not user:
        await call.answer("User not found", show_alert=True)
        return

    username = f"@{user.username}" if user.username else "—"
    await call.message.delete()
    await call.message.answer(
        f"👤 <b>User Info</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: {username}\n"
        f"💲 Balance: <code>{user.balance:.2f}$</code>\n"
        f"💰 Ref Balance: <code>{user.ref_balance:.2f}$</code>\n"
        f"📊 Ref Percent: <code>{percent}%</code>",
        reply_markup=user_manage_inline(user.id)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data == "search_user")
async def search_user_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(
        "🔍 Enter user ID or @username:",
        reply_markup=back_home_inline()
    )
    await state.set_state(AdminState.search_user)
    await call.answer()


@router.message(IsAdmin(), AdminState.search_user)
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip().lstrip("@")

    async with SessionFactory() as session:
        if query.isdigit():
            user = await session.get(User, int(query))
        else:
            result = await session.execute(select(User).where(User.username == query))
            user = result.scalar_one_or_none()

    await state.clear()

    if not user:
        await message.answer("❌ User not found.", reply_markup=back_home_inline())
        return

    username = f"@{user.username}" if user.username else "—"
    await message.answer(
        f"👤 <b>User Info</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: {username}\n"
        f"💲 Balance: <code>{user.balance}$</code>",
        reply_markup=user_manage_inline(user.id)
    )


@router.callback_query(IsAdmin(), F.data.startswith("add_balance:"))
async def add_balance_callback(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split(":")[1])
    await state.update_data(user_id=user_id, action="add")
    await call.message.answer("💰 Enter amount to add:")
    await state.set_state(AdminState.change_balance)
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("remove_balance:"))
async def remove_balance_callback(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split(":")[1])
    await state.update_data(user_id=user_id, action="remove")
    await call.message.answer("💰 Enter amount to remove:")
    await state.set_state(AdminState.change_balance)
    await call.answer()


@router.message(IsAdmin(), AdminState.change_balance)
async def process_change_balance(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid amount. Enter a number:")
        return

    amount = float(message.text)
    data = await state.get_data()
    user_id = data["user_id"]
    action = data["action"]
    await state.clear()

    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("❌ User not found.")
            return

        if action == "add":
            user.balance += amount
        else:
            user.balance = max(0, user.balance - amount)

        await session.commit()
        username = f"@{user.username}" if user.username else f"id:{user.id}"

    sign = "+" if action == "add" else "-"
    await message.answer(
        f"✅ Balance updated!\n"
        f"👤 {username}\n"
        f"💲 {sign}{amount}$ → New balance: <code>{user.balance}$</code>",
        reply_markup=user_manage_inline(user_id)
    )


def plans_manage_inline(plans) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for plan in plans:
        status = "✅" if plan.is_active else "❌"
        months = plan.duration_months
        builder.add(InlineKeyboardButton(
            text=f"{status} {months}mo — {plan.price}$",
            callback_data=f"plan_info:{plan.id}"
        ))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="< Back", callback_data="admin_panel"))
    return builder.as_markup()


def plan_actions_inline(plan_id: int) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💲 Change Price", callback_data=f"change_plan_price:{plan_id}"),
        InlineKeyboardButton(text="🔄 Toggle Active", callback_data=f"toggle_plan:{plan_id}"),
        InlineKeyboardButton(text="< Back", callback_data="manage_plans")
    )
    builder.adjust(2, 1)
    return builder.as_markup()


@router.callback_query(IsAdmin(), F.data == "manage_plans")
async def manage_plans_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        plans = await get_all_plans(session)
    await call.message.delete()
    await call.message.answer("💰 <b>Manage Plans:</b>", reply_markup=plans_manage_inline(plans))
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("plan_info:"))
async def plan_info_callback(call: CallbackQuery):
    plan_id = int(call.data.split(":")[1])
    async with SessionFactory() as session:
        plan = await session.get(Plan, plan_id)
    status = "✅ Active" if plan.is_active else "❌ Inactive"
    months = plan.duration_months
    await call.message.delete()
    await call.message.answer(
        f"📅 <b>Plan: {months} month{'s' if months > 1 else ''}</b>\n\n"
        f"💲 Price: <code>{plan.price}$</code>\n"
        f"Status: {status}",
        reply_markup=plan_actions_inline(plan_id)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("toggle_plan:"))
async def toggle_plan_callback(call: CallbackQuery):
    plan_id = int(call.data.split(":")[1])
    async with SessionFactory() as session:
        plan = await toggle_plan(session, plan_id)
    status = "✅ Active" if plan.is_active else "❌ Inactive"
    await call.answer(f"Plan is now {status}", show_alert=True)
    async with SessionFactory() as session:
        plans = await get_all_plans(session)
    await call.message.delete()
    await call.message.answer("💰 <b>Manage Plans:</b>", reply_markup=plans_manage_inline(plans))


@router.callback_query(IsAdmin(), F.data.startswith("change_plan_price:"))
async def change_plan_price_callback(call: CallbackQuery, state: FSMContext):
    plan_id = int(call.data.split(":")[1])
    await state.update_data(plan_id=plan_id)
    await call.message.answer("💲 Enter new price:")
    await state.set_state(AdminState.change_plan_price)
    await call.answer()


@router.message(IsAdmin(), AdminState.change_plan_price)
async def process_plan_price(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid price. Enter a number:")
        return
    price = float(message.text)
    data = await state.get_data()
    plan_id = data["plan_id"]
    await state.clear()
    async with SessionFactory() as session:
        plan = await update_plan_price(session, plan_id, price)
    months = plan.duration_months
    await message.answer(
        f"✅ Price updated!\n"
        f"📅 {months} month{'s' if months > 1 else ''} → <code>{plan.price}$</code>",
        reply_markup=plan_actions_inline(plan_id)
    )

def locations_manage_inline(locations) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for loc in locations:
        status = "✅" if loc.is_active else "❌"
        builder.add(
            InlineKeyboardButton(text=f"{status} {loc.name}", callback_data=f"toggle_location:{loc.code}"),
            InlineKeyboardButton(text="💲", callback_data=f"location_prices:{loc.code}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_location:{loc.code}")
        )
    builder.adjust(3)
    builder.row(
        InlineKeyboardButton(text="➕ Add Location", callback_data="add_location"),
        InlineKeyboardButton(text="< Back", callback_data="admin_panel")
    )
    return builder.as_markup()


@router.callback_query(IsAdmin(), F.data == "manage_locations")
async def manage_locations_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        locations = await get_all_locations(session)
    await call.message.delete()
    await call.message.answer("🌍 <b>Manage Locations:</b>", reply_markup=locations_manage_inline(locations))
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("toggle_location:"))
async def toggle_location_callback(call: CallbackQuery):
    code = call.data.split(":")[1]
    async with SessionFactory() as session:
        await toggle_location(session, code)
        locations = await get_all_locations(session)
    await call.message.delete()
    await call.message.answer("🌍 <b>Manage Locations:</b>", reply_markup=locations_manage_inline(locations))
    await call.answer()


def location_prices_inline(plans, prices_map, location_code: str) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for plan in plans:
        price = prices_map.get(plan.id, plan.price)
        months = plan.duration_months
        builder.add(InlineKeyboardButton(
            text=f"{months}mo — {price}$",
            callback_data=f"edit_loc_price:{location_code}:{plan.id}"
        ))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="< Back", callback_data="manage_locations"))
    return builder.as_markup()


@router.callback_query(IsAdmin(), F.data.startswith("location_prices:"))
async def location_prices_callback(call: CallbackQuery):
    location_code = call.data.split(":")[1]

    async with SessionFactory() as session:
        from db.crud import get_all_plans, get_prices_for_location
        plans = await get_all_plans(session)
        prices = await get_prices_for_location(session, location_code)
        prices_map = {p.plan_id: p.price for p in prices}
        location = await session.get(Location, location_code)

    await call.message.delete()
    await call.message.answer(
        f"💲 <b>Prices for {location.name}:</b>",
        reply_markup=location_prices_inline(plans, prices_map, location_code)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("edit_loc_price:"))
async def edit_loc_price_callback(call: CallbackQuery, state: FSMContext):
    _, location_code, plan_id = call.data.split(":")
    await state.update_data(location_code=location_code, plan_id=int(plan_id))
    await call.message.answer("💲 Enter new price:")
    await state.set_state(AdminState.change_location_price)
    await call.answer()


@router.message(IsAdmin(), AdminState.change_location_price)
async def process_location_price(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid price. Enter a number:")
        return

    price = float(message.text)
    data = await state.get_data()
    location_code = data["location_code"]
    plan_id = data["plan_id"]
    await state.clear()

    async with SessionFactory() as session:
        from db.crud import set_price, get_all_plans, get_prices_for_location
        await set_price(session, plan_id, location_code, price)
        plans = await get_all_plans(session)
        prices = await get_prices_for_location(session, location_code)
        prices_map = {p.plan_id: p.price for p in prices}
        location = await session.get(Location, location_code)

    await message.answer(
        f"✅ Price updated for {location.name}!",
        reply_markup=location_prices_inline(plans, prices_map, location_code)
    )


def servers_stats_inline(servers, page: int, total_pages: int) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for srv in servers:
        status = "🟢" if srv.is_active else "🔴"
        builder.add(InlineKeyboardButton(
            text=f"{status} {srv.name} | {srv.current_users}/{srv.max_users}",
            callback_data=f"server_info:{srv.id}"
        ))
    builder.adjust(1)

    builder.row(
        InlineKeyboardButton(text="<", callback_data=f"servers_page:{page-1}" if page > 0 else "noop"),
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text=">", callback_data=f"servers_page:{page+1}" if page+1 < total_pages else "noop"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Add Server", callback_data="add_server"),
        InlineKeyboardButton(text="< Back", callback_data="admin_panel")
    )
    return builder.as_markup()


def server_info_inline(server_id: int, is_online: bool) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    toggle_text = "🔴 Disable" if is_online else "🟢 Enable"
    builder.add(
        InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_server:{server_id}"),
        InlineKeyboardButton(text="👥 Max Users", callback_data=f"edit_max_users:{server_id}"),
        InlineKeyboardButton(text="🗑 Delete", callback_data=f"delete_server:{server_id}"),
        InlineKeyboardButton(text="< Back", callback_data="servers_stats:0")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()

@router.callback_query(IsAdmin(), F.data.startswith("delete_server:"))
async def delete_server_callback(call: CallbackQuery):
    server_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        from db.models import Server
        server = await session.get(Server, server_id)
        if not server:
            await call.answer("Server not found", show_alert=True)
            return
        name = server.name
        await session.delete(server)
        await session.commit()

    await call.answer(f"✅ Server {name} deleted", show_alert=True)
    await call.message.delete()
    await call.message.answer(
        "🖥 <b>Servers:</b>",
        reply_markup=await _get_servers_markup(0)
    )


async def _get_servers_markup(page: int):
    async with SessionFactory() as session:
        servers = await get_all_servers(session)
    total = len(servers)
    total_pages = max(1, -(-total // SERVERS_PER_PAGE))
    page_servers = servers[page * SERVERS_PER_PAGE:(page + 1) * SERVERS_PER_PAGE]
    return servers_stats_inline(page_servers, page, total_pages)


@router.callback_query(IsAdmin(), F.data.startswith("servers_stats:"))
async def servers_stats_callback(call: CallbackQuery):
    page = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        servers = await get_all_servers(session)

    total = len(servers)
    total_pages = max(1, -(-total // SERVERS_PER_PAGE))
    page_servers = servers[page * SERVERS_PER_PAGE:(page + 1) * SERVERS_PER_PAGE]

    await call.message.delete()
    await call.message.answer(
        f"🖥 <b>Servers ({total} total):</b>",
        reply_markup=servers_stats_inline(page_servers, page, total_pages)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("server_info:"))
async def server_info_callback(call: CallbackQuery):
    server_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        from db.models import Server
        server = await session.get(Server, server_id)

    alive = await check_server_alive(server)
    status = "🟢 Online" if alive else "🔴 Offline"
    active = "✅ Active" if server.is_active else "❌ Inactive"
    panel_url = f"https://{server.ip}:{server.port}{server.uri_path}"

    await call.message.delete()
    await call.message.answer(
        f"🖥 <b>{server.name}</b>\n\n"
        f"🌍 Location: {server.location_code.upper()}\n"
        f"🔌 IP: <code>{server.ip}:{server.port}</code>\n"
        f"👥 Users: {server.current_users}/{server.max_users}\n"
        f"📡 Status: {status}\n"
        f"🔘 Active: {active}\n"
        f"🔗 Panel: {panel_url}",
        reply_markup=server_info_inline(server_id, alive)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("toggle_server:"))
async def toggle_server_callback(call: CallbackQuery):
    server_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        from db.models import Server
        server = await session.get(Server, server_id)
        server.is_active = not server.is_active
        await session.commit()

    await call.answer(f"Server is now {'✅ Active' if server.is_active else '❌ Inactive'}", show_alert=True)
    await server_info_callback(call)


@router.callback_query(IsAdmin(), F.data == "add_server")
async def add_server_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Enter server name (e.g. DE-1):")
    await state.set_state(AdminState.add_server_name)
    await call.answer()


@router.message(IsAdmin(), AdminState.add_server_name)
async def add_server_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter server IP:")
    await state.set_state(AdminState.add_server_ip)


@router.message(IsAdmin(), AdminState.add_server_ip)
async def add_server_ip(message: Message, state: FSMContext):
    await state.update_data(ip=message.text)
    await message.answer("Enter panel port (default 2053):")
    await state.set_state(AdminState.add_server_port)


@router.message(IsAdmin(), AdminState.add_server_port)
async def add_server_port(message: Message, state: FSMContext):
    port = int(message.text) if message.text.isdigit() else 2053
    await state.update_data(port=port)
    await message.answer("Enter location code (e.g. de, nl, us):")
    await state.set_state(AdminState.add_server_location)


@router.message(IsAdmin(), AdminState.add_server_location)
async def add_server_location(message: Message, state: FSMContext):
    await state.update_data(location_code=message.text.lower())
    await message.answer("Enter inbound ID (default 1):")
    await state.set_state(AdminState.add_server_inbound)


@router.message(IsAdmin(), AdminState.add_server_inbound)
async def add_server_inbound(message: Message, state: FSMContext):
    inbound_id = int(message.text) if message.text.isdigit() else 1
    await state.update_data(inbound_id=inbound_id)
    await message.answer("Enter URI path (e.g. /xk92mq7p/ or just / for default):")
    await state.set_state(AdminState.add_server_uri)


def user_subs_inline(subs, user_id: int) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for sub in subs:
        now = datetime.utcnow()
        status = "🟢" if sub.duration_end > now else "🔴"
        builder.add(InlineKeyboardButton(
            text=f"{status} {sub.geo.upper()} | {sub.duration_end.strftime('%d.%m.%Y')}",
            callback_data=f"admin_sub_info:{sub.id}:{user_id}"
        ))
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="< Back", callback_data=f"user_info:{user_id}"))
    return builder.as_markup()


def admin_sub_actions_inline(sub_id: int, user_id: int) -> InlineKeyboardMarkup:
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🗑 Delete", callback_data=f"admin_delete_sub:{sub_id}:{user_id}"),
        InlineKeyboardButton(text="< Back", callback_data=f"admin_user_subs:{user_id}")
    )
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(IsAdmin(), F.data.startswith("admin_user_subs:"))
async def admin_user_subs_callback(call: CallbackQuery):
    user_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        subs = await get_user_subscriptions(session, user_id)
        user = await session.get(User, user_id)

    if not subs:
        await call.answer("No subscriptions found", show_alert=True)
        return

    await call.message.delete()
    await call.message.answer(
        f"📋 <b>Subscriptions of {user.username or user.id}:</b>",
        reply_markup=user_subs_inline(subs, user_id)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin_sub_info:"))
async def admin_sub_info_callback(call: CallbackQuery):
    _, sub_id, user_id = call.data.split(":")

    async with SessionFactory() as session:
        sub = await get_subscription(session, int(sub_id))

    now = datetime.utcnow()
    is_active = sub.duration_end > now
    status = "🟢 Active" if is_active else "🔴 Expired"
    days_left = (sub.duration_end - now).days if is_active else 0

    await call.message.delete()
    await call.message.answer(
        f"📋 <b>Subscription info:</b>\n\n"
        f"🌍 Location: {sub.geo.upper()}\n"
        f"Status: {status}\n"
        f"📅 Start: {sub.duration_start.strftime('%d.%m.%Y')}\n"
        f"📅 End: {sub.duration_end.strftime('%d.%m.%Y')}\n"
        f"⏳ Days left: {days_left}\n"
        f"👤 Profile: <code>{sub.profile_id}</code>",
        reply_markup=admin_sub_actions_inline(sub.id, int(user_id))
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin_delete_sub:"))
async def admin_delete_sub_callback(call: CallbackQuery):
    _, sub_id, user_id = call.data.split(":")

    async with SessionFactory() as session:
        sub = await get_subscription(session, int(sub_id))
        if not sub:
            await call.answer("Subscription not found", show_alert=True)
            return

        server = await session.get(Server, sub.server_id)

        # Удаляем с сервера
        deleted = await delete_vless_client(server, sub.client_uuid)

        # Удаляем из БД
        await delete_subscription(session, int(sub_id))

        # Уменьшаем счётчик
        if server and server.current_users > 0:
            server.current_users -= 1
            await session.commit()

    status = "✅ Deleted from server and DB" if deleted else "⚠️ Deleted from DB only (server error)"
    await call.answer(status, show_alert=True)

    # Возвращаемся к списку подписок
    async with SessionFactory() as session:
        subs = await get_user_subscriptions(session, int(user_id))
        user = await session.get(User, int(user_id))

    if not subs:
        await call.message.delete()
        await call.message.answer(
            f"📭 No more subscriptions for {user.username or user.id}.",
            reply_markup=user_manage_inline(int(user_id))
        )
        return

    await call.message.delete()
    await call.message.answer(
        f"📋 <b>Subscriptions of {user.username or user.id}:</b>",
        reply_markup=user_subs_inline(subs, int(user_id))
    )

@router.callback_query(IsAdmin(), F.data.startswith("edit_ref_balance:"))
async def edit_ref_balance_callback(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split(":")[1])
    await state.update_data(user_id=user_id)
    await call.message.answer("💰 Enter new referral balance amount (e.g. 10.5):")
    await state.set_state(AdminState.change_ref_balance)
    await call.answer()


@router.message(IsAdmin(), AdminState.change_ref_balance)
async def process_change_ref_balance(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid amount. Enter a number:")
        return

    amount = float(message.text)
    data = await state.get_data()
    user_id = data["user_id"]
    await state.clear()

    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("❌ User not found.")
            return
        user.ref_balance = amount
        await session.commit()
        username = f"@{user.username}" if user.username else f"id:{user.id}"

    await message.answer(
        f"✅ Referral balance updated!\n"
        f"👤 {username}\n"
        f"💰 New ref balance: <code>{amount}$</code>",
        reply_markup=user_manage_inline(user_id)
    )

@router.callback_query(IsAdmin(), F.data == "add_location")
async def add_location_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Enter location code (e.g. de, nl, us):")
    await state.set_state(AdminState.add_location_code)
    await call.answer()


@router.message(IsAdmin(), AdminState.add_location_code)
async def add_location_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.lower().strip())
    await message.answer("Enter location name with flag (e.g. 🇩🇪 Germany):")
    await state.set_state(AdminState.add_location_name)


@router.message(IsAdmin(), AdminState.add_location_name)
async def add_location_name(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    name = message.text.strip()
    await state.clear()

    async with SessionFactory() as session:
        existing = await session.get(Location, code)
        if existing:
            await message.answer("❌ Location with this code already exists.")
            return
        session.add(Location(code=code, name=name, is_active=True))
        await session.commit()

    await message.answer(f"✅ Location {name} added!")

    async with SessionFactory() as session:
        locations = await get_all_locations(session)
    await message.answer("🌍 <b>Manage Locations:</b>", reply_markup=locations_manage_inline(locations))


@router.callback_query(IsAdmin(), F.data.startswith("delete_location:"))
async def delete_location_callback(call: CallbackQuery):
    code = call.data.split(":")[1]

    async with SessionFactory() as session:
        loc = await session.get(Location, code)
        if not loc:
            await call.answer("Location not found", show_alert=True)
            return
        name = loc.name
        await session.delete(loc)
        await session.commit()
        locations = await get_all_locations(session)

    await call.answer(f"✅ {name} deleted", show_alert=True)
    await call.message.delete()
    await call.message.answer("🌍 <b>Manage Locations:</b>", reply_markup=locations_manage_inline(locations))


@router.message(IsAdmin(), AdminState.add_server_uri)
async def add_server_uri(message: Message, state: FSMContext):
    uri_path = message.text.strip()
    if not uri_path.startswith("/"):
        uri_path = "/" + uri_path
    if not uri_path.endswith("/"):
        uri_path = uri_path + "/"

    data = await state.get_data()
    await state.clear()

    async with SessionFactory() as session:
        server = await add_server(
            session,
            name=data["name"],
            ip=data["ip"],
            port=data["port"],
            location_code=data["location_code"],
            inbound_id=data["inbound_id"],
            uri_path=uri_path
        )

    await message.answer(
        f"✅ Server added!\n"
        f"🖥 {server.name} ({server.location_code.upper()})\n"
        f"🔌 {server.ip}:{server.port}{server.uri_path}"
    )


@router.callback_query(IsAdmin(), F.data.startswith("edit_max_users:"))
async def edit_max_users_callback(call: CallbackQuery, state: FSMContext):
    server_id = int(call.data.split(":")[1])
    await state.update_data(server_id=server_id)
    await call.message.answer("👥 Enter new max users limit:")
    await state.set_state(AdminState.edit_max_users)
    await call.answer()


@router.message(IsAdmin(), AdminState.edit_max_users)
async def process_edit_max_users(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Enter a number:")
        return

    max_users = int(message.text)
    data = await state.get_data()
    server_id = data["server_id"]
    await state.clear()

    async with SessionFactory() as session:
        from db.models import Server
        server = await session.get(Server, server_id)
        server.max_users = max_users
        await session.commit()

    await message.answer(f"✅ Max users updated to {max_users}")


@router.callback_query(IsAdmin(), F.data == "admin_broadcast")
async def admin_broadcast_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer(
        "📢 <b>Broadcast</b>\n\n"
        "Send a message to all users.\n"
        "You can use HTML formatting.\n\n"
        "Enter your message:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")]
        ])
    )
    await state.set_state(AdminState.broadcast_text)
    await call.answer()


@router.message(IsAdmin(), AdminState.broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    await state.clear()

    async with SessionFactory() as session:
        from sqlalchemy import select
        from db.models import User
        result = await session.execute(select(User))
        users = result.scalars().all()

    total = len(users)
    success = 0
    failed = 0

    status_msg = await message.answer(f"📢 Sending to {total} users...")

    for user in users:
        try:
            await message.bot.send_message(
                user.id,
                message.text or message.caption or "",
                parse_mode="HTML"
            )
            success += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"📢 <b>Broadcast complete</b>\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"👥 Total: {total}"
    )


from db.crud import get_all_promos, create_promo, delete_promo, toggle_promo
from db.models import PromoCode


def promos_inline(promos: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for promo in promos:
        status = "✅" if promo.is_active else "❌"
        builder.add(InlineKeyboardButton(
            text=f"{status} {promo.code} ({promo.used_count}/{promo.max_uses})",
            callback_data=f"promo_info:{promo.id}"
        ))
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="➕ Create", callback_data="promo_create"),
        InlineKeyboardButton(text="< Back", callback_data="admin_panel")
    )
    return builder.as_markup()


def promo_info_inline(promo_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🔄 Toggle", callback_data=f"promo_toggle:{promo_id}"),
        InlineKeyboardButton(text="🗑 Delete", callback_data=f"promo_delete:{promo_id}"),
        InlineKeyboardButton(text="< Back", callback_data="admin_promos")
    )
    builder.adjust(2, 1)
    return builder.as_markup()


@router.callback_query(IsAdmin(), F.data == "admin_promos")
async def admin_promos_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        promos = await get_all_promos(session)

    await call.message.delete()
    await call.message.answer(
        f"🎁 <b>Promo Codes</b> ({len(promos)} total)",
        reply_markup=promos_inline(promos)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("promo_info:"))
async def promo_info_callback(call: CallbackQuery):
    promo_id = int(call.data.split(":")[1])

    async with SessionFactory() as session:
        promo = await session.get(PromoCode, promo_id)
        await session.refresh(promo, ["plan", "location"])

    expires = promo.expires_at.strftime("%d.%m.%Y") if promo.expires_at else "No limit"
    status = "✅ Active" if promo.is_active else "❌ Inactive"
    plan_str = f"{promo.plan.duration_months} month(s)" if promo.plan else f"{promo.duration_days} day(s)"

    await call.message.delete()
    await call.message.answer(
        f"🎁 <b>Promo: {promo.code}</b>\n\n"
        f"📊 Status: {status}\n"
        f"🌍 Location: {promo.location.name}\n"
        f"📅 Duration: {plan_str}\n"
        f"👥 Uses: {promo.used_count}/{promo.max_uses}\n"
        f"⏳ Expires: {expires}",
        reply_markup=promo_info_inline(promo_id)
    )
    await call.answer()


@router.callback_query(IsAdmin(), F.data.startswith("promo_toggle:"))
async def promo_toggle_callback(call: CallbackQuery):
    promo_id = int(call.data.split(":")[1])
    async with SessionFactory() as session:
        await toggle_promo(session, promo_id)
    await promo_info_callback(call)


@router.callback_query(IsAdmin(), F.data.startswith("promo_delete:"))
async def promo_delete_callback(call: CallbackQuery):
    promo_id = int(call.data.split(":")[1])
    async with SessionFactory() as session:
        await delete_promo(session, promo_id)

    await call.answer("✅ Deleted", show_alert=True)
    async with SessionFactory() as session:
        promos = await get_all_promos(session)
    await call.message.delete()
    await call.message.answer(
        f"🎁 <b>Promo Codes</b> ({len(promos)} total)",
        reply_markup=promos_inline(promos)
    )


@router.callback_query(IsAdmin(), F.data == "promo_create")
async def promo_create_callback(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Enter promo code (e.g. SUMMER2026):")
    await state.set_state(AdminState.promo_code)
    await call.answer()


@router.message(IsAdmin(), AdminState.promo_code)
async def process_promo_code_input(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    async with SessionFactory() as session:
        existing = await get_promo(session, code)
    if existing:
        await message.answer("❌ This code already exists. Enter another:")
        return
    await state.update_data(code=code)

    async with SessionFactory() as session:
        plans = await get_all_plans(session)

    builder = InlineKeyboardBuilder()

    # Короткие сроки
    for days, label in [(1, "1 day"), (3, "3 days"), (7, "7 days"), (14, "14 days")]:
        builder.add(InlineKeyboardButton(
            text=label,
            callback_data=f"promo_set_days:{days}"
        ))
    builder.adjust(4)

    # Планы по месяцам
    for plan in plans:
        if plan.is_active:
            builder.add(InlineKeyboardButton(
                text=f"{plan.duration_months} month(s)",
                callback_data=f"promo_set_plan:{plan.id}"
            ))
    builder.adjust(4, 2)

    await message.answer("Select duration:", reply_markup=builder.as_markup())
    await state.set_state(AdminState.promo_plan)


@router.callback_query(IsAdmin(), AdminState.promo_location, F.data.startswith("promo_set_loc:"))
async def process_promo_location(call: CallbackQuery, state: FSMContext):
    location_code = call.data.split(":")[1]
    await state.update_data(location_code=location_code)
    await call.message.answer("Enter max uses (e.g. 1 or 100):")
    await state.set_state(AdminState.promo_uses)
    await call.answer()


@router.message(IsAdmin(), AdminState.promo_uses)
async def process_promo_uses(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Enter a number:")
        return
    await state.update_data(max_uses=int(message.text))
    await message.answer(
        "Enter expiry date (DD.MM.YYYY) or send - for no limit:"
    )
    await state.set_state(AdminState.promo_expires)


@router.message(IsAdmin(), AdminState.promo_expires)
async def process_promo_expires(message: Message, state: FSMContext):
    expires_at = None
    if message.text.strip() != "-":
        try:
            expires_at = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        except ValueError:
            await message.answer("❌ Invalid date format. Use DD.MM.YYYY or -:")
            return

    data = await state.get_data()
    await state.clear()

    async with SessionFactory() as session:
        promo = await create_promo(
            session,
            code=data["code"],
            plan_id=data.get("plan_id"),
            location_code=data["location_code"],
            max_uses=data["max_uses"],
            expires_at=expires_at,
            duration_days=data.get("duration_days")
        )

    duration_str = f"{data['duration_days']} day(s)" if data.get("duration_days") else f"from plan"
    expires_str = expires_at.strftime("%d.%m.%Y") if expires_at else "No limit"
    await message.answer(
        f"✅ <b>Promo code created!</b>\n\n"
        f"🎁 Code: <code>{promo.code}</code>\n"
        f"⏳ Duration: {duration_str}\n"
        f"👥 Max uses: {promo.max_uses}\n"
        f"📅 Expires: {expires_str}"
    )

@router.callback_query(IsAdmin(), AdminState.promo_plan, F.data.startswith("promo_set_days:"))
async def process_promo_days(call: CallbackQuery, state: FSMContext):
    days = int(call.data.split(":")[1])
    await state.update_data(plan_id=None, duration_days=days)

    async with SessionFactory() as session:
        locations = await get_all_locations(session)
    builder = InlineKeyboardBuilder()
    for loc in locations:
        if loc.is_active:
            builder.add(InlineKeyboardButton(
                text=loc.name,
                callback_data=f"promo_set_loc:{loc.code}"
            ))
    builder.adjust(2)
    await call.message.answer("Select location:", reply_markup=builder.as_markup())
    await state.set_state(AdminState.promo_location)
    await call.answer()


@router.callback_query(IsAdmin(), AdminState.promo_plan, F.data.startswith("promo_set_plan:"))
async def process_promo_plan(call: CallbackQuery, state: FSMContext):
    plan_id = int(call.data.split(":")[1])
    await state.update_data(plan_id=plan_id, duration_days=None)

    async with SessionFactory() as session:
        locations = await get_all_locations(session)
    builder = InlineKeyboardBuilder()
    for loc in locations:
        if loc.is_active:
            builder.add(InlineKeyboardButton(
                text=loc.name,
                callback_data=f"promo_set_loc:{loc.code}"
            ))
    builder.adjust(2)
    await call.message.answer("Select location:", reply_markup=builder.as_markup())
    await state.set_state(AdminState.promo_location)
    await call.answer()
