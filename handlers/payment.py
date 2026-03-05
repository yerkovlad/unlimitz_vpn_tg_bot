from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp

from db.database import SessionFactory
from db.crud import update_balance
from payments.crypto import create_invoice, check_invoice
from payments.nowpayments import create_payment, check_payment, BASE_URL, NOWPAYMENTS_API_KEY, get_min_amount
from keyboards.inline import back_home_inline

router = Router()


class PaymentState(StatesGroup):
    waiting_amount_crypto = State()
    waiting_amount_now = State()


CURRENCIES = [
    ("USDT (TRC20)", "usdttrc20"),
    ("USDT (ERC20)", "usdterc20"),
    ("BTC", "btc"),
    ("ETH", "eth"),
    ("SOL", "sol"),
    ("BNB", "bnbbsc"),
]


def top_up_method_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="🪙 CryptoBot", callback_data="topup_crypto"),
        InlineKeyboardButton(text="💎 NOWPayments", callback_data="topup_now"),
    )
    builder.adjust(2)
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


def now_currency_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name, code in CURRENCIES:
        builder.add(InlineKeyboardButton(
            text=name,
            callback_data=f"now_currency:{code}"
        ))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="< Back", callback_data="top_up"))
    return builder.as_markup()


def now_payment_inline(payment_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="✅ Check Payment", callback_data=f"now_check:{payment_id}"),
        InlineKeyboardButton(text="🏠 Home", callback_data="back_home")
    )
    builder.adjust(1)
    return builder.as_markup()


# ── Top Up entry point ──────────────────────────────────────────────

@router.callback_query(F.data == "top_up")
async def top_up_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "💲 <b>Select payment method:</b>",
        reply_markup=top_up_method_inline()
    )
    await call.answer()


# ── CryptoBot ───────────────────────────────────────────────────────

@router.callback_query(F.data == "topup_crypto")
async def topup_crypto_callback(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("🪙 <b>Enter amount in USD (min $1):</b>")
    await state.set_state(PaymentState.waiting_amount_crypto)
    await call.answer()


@router.message(PaymentState.waiting_amount_crypto)
async def process_crypto_amount(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid amount. Enter a number:")
        return

    amount = float(message.text)
    if amount < 1:
        await message.answer("❌ Minimum amount is $1. Enter again:")
        return

    await state.clear()

    invoice = await create_invoice(
        amount=amount,
        user_id=message.from_user.id,
        description=f"Unlimitz VPN — top up {amount}$"
    )

    await message.answer(
        f"🧾 <b>Invoice created</b>\n\n"
        f"💲 Amount: <code>{amount} USDT</code>\n"
        f"⏳ Expires in: 1 hour\n\n"
        f"Press <b>Pay</b> to open CryptoBot.",
        reply_markup=payment_inline(invoice.bot_invoice_url, invoice.invoice_id)
    )


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(call: CallbackQuery):
    invoice_id = int(call.data.split(":")[1])

    paid = await check_invoice(invoice_id)
    if not paid:
        await call.answer("❌ Payment not found yet. Try again.", show_alert=True)
        return

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
        reply_markup=back_home_inline()
    )
    await call.answer()


# ── NOWPayments ─────────────────────────────────────────────────────

@router.callback_query(F.data == "topup_now")
async def topup_now_callback(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer(
        "💎 <b>Select currency:</b>",
        reply_markup=now_currency_inline()
    )
    await call.answer()


@router.callback_query(F.data.startswith("now_currency:"))
async def now_currency_callback(call: CallbackQuery, state: FSMContext):
    currency = call.data.split(":")[1]
    await state.update_data(currency=currency)
    await call.message.delete()
    await call.message.answer("💎 <b>Enter amount in USD:</b>")
    await state.set_state(PaymentState.waiting_amount_now)
    await call.answer()


@router.message(PaymentState.waiting_amount_now)
async def process_now_amount(message: Message, state: FSMContext):
    if not message.text.replace(".", "").isdigit():
        await message.answer("❌ Invalid amount. Enter a number:")
        return

    amount = float(message.text)
    data = await state.get_data()
    currency = data.get("currency", "usdttrc20")

    min_amount = await get_min_amount(currency)
    if amount < min_amount:
        await message.answer(f"❌ Minimum amount is ${min_amount:.2f}. Enter again:")
        return

    await state.clear()

    payment = await create_payment(amount, message.from_user.id)
    if not payment:
        await message.answer("❌ Payment creation failed. Try again.")
        return

    pay_address = payment.get("pay_address")
    pay_amount = payment.get("pay_amount")
    pay_currency = payment.get("pay_currency", currency).upper()
    payment_id = str(payment.get("payment_id"))

    await message.answer(
        f"💎 <b>Payment created</b>\n\n"
        f"💲 Amount: <code>{amount}$</code>\n"
        f"💰 Pay: <code>{pay_amount} {pay_currency}</code>\n\n"
        f"📬 <b>Send to address:</b>\n"
        f"<code>{pay_address}</code>\n\n"
        f"⏳ After sending press <b>Check Payment</b>",
        reply_markup=now_payment_inline(payment_id)
    )


@router.callback_query(F.data.startswith("now_check:"))
async def now_check_callback(call: CallbackQuery):
    payment_id = call.data.split(":")[1]

    status = await check_payment(payment_id)

    if status not in ("finished", "confirmed", "partially_paid"):
        await call.answer(f"⏳ Status: {status}. Try again later.", show_alert=True)
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/payment/{payment_id}",
            headers={"x-api-key": NOWPAYMENTS_API_KEY}
        ) as r:
            data = await r.json()
            amount = float(data.get("price_amount", 0))

    async with SessionFactory() as session:
        user = await update_balance(session, call.from_user.id, amount)

    await call.message.delete()
    await call.message.answer(
        f"✅ <b>Payment confirmed!</b>\n\n"
        f"💲 Added: <code>{amount}$</code>\n"
        f"💰 New balance: <code>{user.balance}$</code>",
        reply_markup=back_home_inline()
    )
    await call.answer()