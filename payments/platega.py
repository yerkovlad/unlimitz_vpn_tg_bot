import aiohttp
import logging
import time
import json
from config import PLATEGA_MERCHANT_ID, PLATEGA_SECRET

logger = logging.getLogger(__name__)

BASE_URL = "https://app.platega.io"

HEADERS = {
    "X-MerchantId": PLATEGA_MERCHANT_ID,
    "X-Secret": PLATEGA_SECRET,
    "Content-Type": "application/json"
}

PAYMENT_METHODS = {
    "card": 11,
    "sbp": 2,
}


async def create_invoice(amount: float, user_id: int, method: str = "sbp") -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/transaction/process",
            headers=HEADERS,
            json={
                "paymentMethod": PAYMENT_METHODS.get(method, 2),
                "Description": "Unlimitz VPN top up",
                "paymentDetails": {
                    "amount": amount,
                    "currency": "RUB",
                    "description": "Unlimitz VPN top up",
                    "payload": f"user_{user_id}_{int(time.time())}"
                }
            }
        ) as r:
            text = await r.text()
            logger.info("Platega create status: %s, response: %s", r.status, text)
            try:
                return json.loads(text)
            except Exception:
                logger.error("Platega non-JSON response: %s", text)
                return None


async def check_invoice(transaction_id: str) -> str | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/transaction/{transaction_id}",
            headers=HEADERS
        ) as r:
            text = await r.text()
            logger.info("Platega check status: %s, response: %s", r.status, text)
            try:
                data = json.loads(text)
                return data.get("status")
            except Exception:
                return None


async def get_invoice(transaction_id: str) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BASE_URL}/transaction/{transaction_id}",
            headers=HEADERS
        ) as r:
            text = await r.text()
            try:
                return json.loads(text)
            except Exception:
                return None