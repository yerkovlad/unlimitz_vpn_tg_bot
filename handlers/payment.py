from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import json

from db.database import SessionFactory
from db.crud import update_balance, get_user_lang
from payments.crypto import create_invoice, check_invoice
from payments.nowpayments import create_payment, check_payment, BASE_URL as NOW_BASE_URL, NOWPAYMENTS_API_KEY, get_min_amount
from payments.platega import create_invoice as platega_create, check_invoice as platega_check, get_invoice as platega_get
from keyboards.inline import back_home_inline
from locales import t

router = Router()


class PaymentState(StatesGroup):
    waiting_amount_crypto = State()
    waiting_amount_now = State()
    waiting_amount_card = State()
    waiting_amount_sbp = State()


CURRENCIES = [
    ("USDT (TRC20)", "usdttrc20"),
    ("USDT (ERC20)", "usdterc20"),
    ("BTC", "btc"),
    ("ETH", "eth"),
    ("SOL", "sol"),
    ("BNB", "bnbbsc"),
]


def top_up_method_inline(lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_cryptobot", lang), callback_data="topup_crypto"),
        InlineKeyboardButton(text=t("btn_nowpayments", lang), callback_data="topup_now"),
        InlineKeyboardButton(text=t("btn_card", lang), callback_data="topup_card"),
        InlineKeyboardButton(text=t("btn_sbp", lang), callback_data="topup_sbp"),
    )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


def payment_inline(pay_url: str, invoice_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_pay", lang), url=pay_url),
        InlineKeyboardButton(text=t("btn_check", lang), callback_data=f"check_payment:{invoice_id}"),
    )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


def now_currency_inline(lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for name, code in CURRENCIES:
        builder.add(InlineKeyboardButton(text=name, callback_data=f"now_currency:{code}"))
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=t("btn_back_short", lang), callback_data="top_up"))
    return builder.as_markup()


def now_payment_inline(payment_id: str, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_check", lang), callback_data=f"now_check:{payment_id}"),
        InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home")
    )
    builder.adjust(1)
    return builder.as_markup()


def platega_payment_inline(pay_url: str, transaction_id: str, lang: str = "en") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text=t("btn_pay", lang), url=pay_url),
        InlineKeyboardButton(text=t("btn_check", lang), callback_data=f"platega_check:{transaction_id}"),
    )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=t("btn_back", lang), callback_data="back_home"))
    return builder.as_markup()


# ── Top Up entry point ──────────────────────────────────────────────

@router.callback_query(F.data == "top_up")
async def top_up_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(
        t("top_up_method", lang),
        reply_markup=top_up_method_inline(lang)
    )
    await call.answer()


# ── CryptoBot ───────────────────────────────────────────────────────

@router.callback_query(F.data == "topup_crypto")
async def topup_crypto_callback(call: CallbackQuery, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(f"🪙 <b>{t('enter_amount_usd', lang)}</b>")
    await state.set_state(PaymentState.waiting_amount_crypto)
    await call.answer()


@router.message(PaymentState.waiting_amount_crypto)
async def process_crypto_amount(message: Message, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, message.from_user.id)
    if not message.text.replace(".", "").isdigit():
        await message.answer(t("invalid_amount", lang))
        return
    amount = float(message.text)
    if amount < 1:
        await message.answer(t("min_amount_usd", lang))
        return
    await state.clear()

    invoice = await create_invoice(
        amount=amount,
        user_id=message.from_user.id,
        description=f"Unlimitz VPN — top up {amount}$"
    )
    await message.answer(
        t("invoice_created", lang, amount=amount),
        reply_markup=payment_inline(invoice.bot_invoice_url, invoice.invoice_id, lang)
    )


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    invoice_id = int(call.data.split(":")[1])
    paid = await check_invoice(invoice_id)
    if not paid:
        await call.answer(t("payment_not_paid", lang, status="not paid"), show_alert=True)
        return

    from payments.crypto import crypto
    invoice = await crypto.get_invoices(invoice_ids=invoice_id)
    amount = float(invoice.amount)

    async with SessionFactory() as session:
        user = await update_balance(session, call.from_user.id, amount)

    await call.message.delete()
    await call.message.answer(
        t("payment_success", lang, amount=amount, balance=round(user.balance, 2)),
        reply_markup=back_home_inline(lang)
    )
    await call.answer()


# ── NOWPayments ─────────────────────────────────────────────────────

@router.callback_query(F.data == "topup_now")
async def topup_now_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(
        t("btn_select_currency", lang),
        reply_markup=now_currency_inline(lang)
    )
    await call.answer()


@router.callback_query(F.data.startswith("now_currency:"))
async def now_currency_callback(call: CallbackQuery, state: FSMContext):
    currency = call.data.split(":")[1]
    await state.update_data(currency=currency)
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(f"💎 <b>{t('enter_amount_usd', lang)}</b>")
    await state.set_state(PaymentState.waiting_amount_now)
    await call.answer()


@router.message(PaymentState.waiting_amount_now)
async def process_now_amount(message: Message, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, message.from_user.id)
    if not message.text.replace(".", "").isdigit():
        await message.answer(t("invalid_amount", lang))
        return
    amount = float(message.text)
    data = await state.get_data()
    currency = data.get("currency", "usdttrc20")

    min_amount = await get_min_amount(currency)
    if amount < min_amount:
        await message.answer(t("min_amount_crypto", lang, min=f"{min_amount:.2f}"))
        return

    await state.clear()

    payment = await create_payment(amount, message.from_user.id)
    if not payment:
        await message.answer(t("payment_failed", lang))
        return

    pay_address = payment.get("pay_address")
    pay_amount = payment.get("pay_amount")
    pay_currency = payment.get("pay_currency", currency).upper()
    payment_id = str(payment.get("payment_id"))

    await message.answer(
        t("now_payment_created", lang,
          amount=amount,
          pay_amount=pay_amount,
          currency=pay_currency,
          address=pay_address),
        reply_markup=now_payment_inline(payment_id, lang)
    )


@router.callback_query(F.data.startswith("now_check:"))
async def now_check_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    payment_id = call.data.split(":")[1]
    status = await check_payment(payment_id)

    if status not in ("finished", "confirmed", "partially_paid"):
        await call.answer(t("payment_not_paid", lang, status=status), show_alert=True)
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{NOW_BASE_URL}/payment/{payment_id}",
            headers={"x-api-key": NOWPAYMENTS_API_KEY}
        ) as r:
            data = json.loads(await r.text())
            amount = float(data.get("price_amount", 0))

    async with SessionFactory() as session:
        user = await update_balance(session, call.from_user.id, amount)

    await call.message.delete()
    await call.message.answer(
        t("payment_success", lang, amount=amount, balance=round(user.balance, 2)),
        reply_markup=back_home_inline(lang)
    )
    await call.answer()


# ── Platega (Card / SBP) ────────────────────────────────────────────

@router.callback_query(F.data == "topup_card")
async def topup_card_callback(call: CallbackQuery, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(f"💳 <b>{t('enter_amount_rub', lang)}</b>")
    await state.set_state(PaymentState.waiting_amount_card)
    await call.answer()


@router.callback_query(F.data == "topup_sbp")
async def topup_sbp_callback(call: CallbackQuery, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)
    await call.message.delete()
    await call.message.answer(f"⚡ <b>{t('enter_amount_rub', lang)}</b>")
    await state.set_state(PaymentState.waiting_amount_sbp)
    await call.answer()


@router.message(PaymentState.waiting_amount_card)
async def process_card_amount(message: Message, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, message.from_user.id)
    if not message.text.replace(".", "").isdigit():
        await message.answer(t("invalid_amount", lang))
        return
    amount = float(message.text)
    if amount < 100:
        await message.answer(t("min_amount_rub", lang))
        return
    await state.clear()

    invoice = await platega_create(amount, message.from_user.id, method="card")
    if not invoice or not invoice.get("transactionId"):
        await message.answer(t("payment_failed", lang))
        return

    await message.answer(
        t("card_payment", lang, amount=amount),
        reply_markup=platega_payment_inline(invoice.get("redirect"), str(invoice.get("transactionId")), lang)
    )


@router.message(PaymentState.waiting_amount_sbp)
async def process_sbp_amount(message: Message, state: FSMContext):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, message.from_user.id)
    if not message.text.replace(".", "").isdigit():
        await message.answer(t("invalid_amount", lang))
        return
    amount = float(message.text)
    if amount < 100:
        await message.answer(t("min_amount_rub", lang))
        return
    await state.clear()

    invoice = await platega_create(amount, message.from_user.id, method="sbp")
    if not invoice or not invoice.get("transactionId"):
        await message.answer(t("payment_failed", lang))
        return

    await message.answer(
        t("sbp_payment", lang, amount=amount),
        reply_markup=platega_payment_inline(invoice.get("redirect"), str(invoice.get("transactionId")), lang)
    )


@router.callback_query(F.data.startswith("platega_check:"))
async def platega_check_callback(call: CallbackQuery):
    async with SessionFactory() as session:
        lang = await get_user_lang(session, call.from_user.id)

    transaction_id = call.data.split(":")[1]
    status = await platega_check(transaction_id)
    if status != "CONFIRMED":
        await call.answer(t("payment_not_paid", lang, status=status), show_alert=True)
        return

    invoice = await platega_get(transaction_id)
    amount_rub = float(invoice.get("paymentDetails", {}).get("amount", 0))
    usd_amount = round(amount_rub / 90, 2)

    async with SessionFactory() as session:
        user = await update_balance(session, call.from_user.id, usd_amount)

    await call.message.delete()
    await call.message.answer(
        t("rub_success", lang, usd=usd_amount, rub=amount_rub, balance=round(user.balance, 2)),
        reply_markup=back_home_inline(lang)
    )
    await call.answer()