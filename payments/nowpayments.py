import aiohttp
import logging

from config import NOWPAYMENTS_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://api.nowpayments.io/v1"


async def create_payment(amount: float, user_id: int) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/payment",
            headers={
                "x-api-key": NOWPAYMENTS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "price_amount": amount,
                "price_currency": "usd",
                "pay_currency": "usdttrc20",
                "order_id": f"user_{user_id}_{int(__import__('time').time())}",
                "order_description": f"Unlimitz VPN top up {amount}$"
            }
        ) as r:
            data = await r.json()
            if "payment_id" in data:
                return data
            logger.error("NOWPayments create error: %s", data)
            return None


async def check_payment(payment_id: str) -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/payment/{payment_id}",
            headers={"x-api-key": NOWPAYMENTS_API_KEY}
        ) as r:
            data = await r.json()
            return data.get("payment_status")


async def get_min_amount(currency: str = "usdttrc20") -> float:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/min-amount?currency_from={currency}",
            headers={"x-api-key": NOWPAYMENTS_API_KEY}
        ) as r:
            data = await r.json()
            return float(data.get("min_amount", 1.0))