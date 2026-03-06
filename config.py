import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ADMIN_ID: str = os.getenv("ADMIN_ID")
PANEL_URL = os.getenv("PANEL_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
INBOUND_ID = int(os.getenv("INBOUND_ID"))
PANEL_USERNAME: str = os.getenv("PANEL_USERNAME", "admin")
PANEL_PASSWORD: str = os.getenv("PANEL_PASSWORD", "admin")
CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN")
NOWPAYMENTS_API_KEY: str = os.getenv("NOWPAYMENTS_API_KEY")
PLATEGA_MERCHANT_ID: str = os.getenv("PLATEGA_MERCHANT_ID")
PLATEGA_SECRET: str = os.getenv("PLATEGA_SECRET")