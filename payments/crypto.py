from aiocryptopay import AioCryptoPay, Networks

from config import CRYPTOBOT_TOKEN

crypto = AioCryptoPay(token=CRYPTOBOT_TOKEN, network=Networks.MAIN_NET)


async def create_invoice(amount: float, user_id: int, description: str) -> dict:
    invoice = await crypto.create_invoice(
        asset="USDT",
        amount=amount,
        description=description,
        payload=str(user_id),
        allow_comments=False,
        allow_anonymous=False,
        expires_in=3600
    )
    return invoice


async def check_invoice(invoice_id: int) -> bool:
    invoice = await crypto.get_invoices(invoice_ids=invoice_id)
    if invoice and invoice.status == "paid":
        return True
    return False


async def close():
    await crypto.close()