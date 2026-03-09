from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from locales import t


def about_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌐 GitHub", url="https://github.com"),
        InlineKeyboardButton(text="❌ Close", callback_data="close")
    )
    return builder.as_markup()


def confirm_inline(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm:{action}"),
        InlineKeyboardButton(text="❌ No", callback_data="close")
    )
    return builder.as_markup()


def menu_inline(lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_buy", lang), callback_data="buy_vpn"),
        InlineKeyboardButton(text=t("btn_profile", lang), callback_data="profile"),
        InlineKeyboardButton(text=t("btn_earn", lang), callback_data="earn"),
        InlineKeyboardButton(text=t("btn_support", lang), url="https://t.me/unlimitz"),
        InlineKeyboardButton(text=t("btn_about", lang), callback_data="about_us"),
        InlineKeyboardButton(text=t("btn_channel", lang), url="https://t.me/unlimitzproject"),
        InlineKeyboardButton(text=t("btn_terms", lang), callback_data="terms"),
        InlineKeyboardButton(text=t("btn_website", lang), url="https://unlimitz.space/"),
        InlineKeyboardButton(text=t("btn_promo", lang), callback_data="promo"),
        InlineKeyboardButton(text=t("btn_info", lang), callback_data="info")
    )
    builder.adjust(1, 1, 2, 2, 1, 1, 1, 1)
    return builder.as_markup()


def back_home_inline(lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home")
    )
    return builder.as_markup()

def profile_keyboard_inline(is_admin: bool = False, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_my_subs", lang), callback_data="my_subs"),
        InlineKeyboardButton(text=t("btn_top_up", lang), callback_data="top_up"),
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home")
    )
    if is_admin:
        builder.add(
            InlineKeyboardButton(text=t("btn_admin", lang), callback_data="admin_panel")
        )
    builder.adjust(2, 1)
    return builder.as_markup()


def admin_panel_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="👥 Users List", callback_data="users_list:0"),
        InlineKeyboardButton(text="🔍 Search User", callback_data="search_user"),
        InlineKeyboardButton(text="💰 Manage Plans", callback_data="manage_plans"),
        InlineKeyboardButton(text="🌍 Manage Locations", callback_data="manage_locations"),
        InlineKeyboardButton(text="🖥 Servers", callback_data="servers_stats:0"),
        InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats"),
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="🎁 Promo Codes", callback_data="admin_promos"),
        InlineKeyboardButton(text="🏠 Home", callback_data="back_home")
    )
    builder.adjust(2, 1, 1, 2, 1, 1, 1)
    return builder.as_markup()


def user_manage_inline(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="➕ Add Balance", callback_data=f"add_balance:{user_id}"),
        InlineKeyboardButton(text="➖ Remove Balance", callback_data=f"remove_balance:{user_id}"),
        InlineKeyboardButton(text="💰 Edit Ref Balance", callback_data=f"edit_ref_balance:{user_id}"),
        InlineKeyboardButton(text="📊 Edit Ref %", callback_data=f"change_ref_percent:{user_id}"),
        InlineKeyboardButton(text="📋 Subscriptions", callback_data=f"admin_user_subs:{user_id}"),
        InlineKeyboardButton(text="◀️ Back", callback_data="users_list:0")
    )
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()