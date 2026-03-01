import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.database import SessionFactory
from db.crud import get_or_create_user, update_balance
from payments.crypto import create_invoice, check_invoice

router = Router()

AMOUNTS = [1, 2, 5, 10, 20, 50, 100]


def top_up_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amount in AMOUNTS:
        builder.add(InlineKeyboardButton(
            text=f"{amount} $",
            callback_data=f"topup_amount:{amount}"
        ))
    builder.adjust(3, 2)
    builder.row(InlineKeyboardButton(text="🏠 Home", callback_data="back_home"))
    return builder.as_markup()


def payment_inline(pay_url: str, invoice_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="💳 Pay", url=pay_url),
        InlineKeyboardButton(text="✅ Check Payment", callback_data=f"check_payment:{invoice_id}"),
    )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠 Home", callback_data="back_home"))
    return builder.as_markup()


@router.callback_query(F.data == "top_up")
async def top_up_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "💲 <b>Select amount to top up:</b>",
        reply_markup=top_up_inline()
    )
    await call.answer()


@router.callback_query(F.data.startswith("topup_amount:"))
async def topup_amount_callback(call: CallbackQuery):
    amount = float(call.data.split(":")[1])

    invoice = await create_invoice(
        amount=amount,
        user_id=call.from_user.id,
        description=f"Unlimitz VPN — top up {amount}$"
    )

    await call.message.delete()
    await call.message.answer(
        f"🧾 <b>Invoice created</b>\n\n"
        f"💲 Amount: <code>{amount} USDT</code>\n"
        f"⏳ Expires in: 1 hour\n\n"
        f"Press <b>Pay</b> to open CryptoBot and complete payment.\n"
        f"After payment press <b>Check Payment</b>.",
        reply_markup=payment_inline(invoice.bot_invoice_url, invoice.invoice_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(call: CallbackQuery):
    invoice_id = int(call.data.split(":")[1])

    paid = await check_invoice(invoice_id)

    if not paid:
        await call.answer("❌ Payment not found yet. Try again.", show_alert=True)
        return

    # Получаем сумму инвойса
    from payments.crypto import crypto
    invoice = await crypto.get_invoices(invoice_ids=invoice_id)
    amount = float(invoice.amount)

    async with SessionFactory() as session:
        user = await update_balance(session, call.from_user.id, amount)

    await call.message.delete()
    await call.message.answer(
        f"✅ <b>Payment successful!</b>\n\n"
        f"💲 Added: <code>{amount}$</code>\n"
        f"💰 New balance: <code>{user.balance}$</code>",
        reply_markup=__import__('keyboards.inline', fromlist=['back_home_inline']).back_home_inline()
    )
    await call.answer()