# Unlimitz VPN Telegram Bot

A Telegram bot for managing VPN subscriptions, payments, and referral bonuses. Built with `aiogram` and `SQLAlchemy`, this bot supports automatic VPN user provisioning through VLESS, multiple payment gateways, promo codes, and a referral system.

## Key Features

- Telegram bot built with `aiogram`.
- VPN subscription purchase flow with location selection and plan management.
- SQLite database backend using `SQLAlchemy` and async sessions.
- Payment integrations:
  - CryptoPay (`aiocryptopay`)
  - NOWPayments
  - Platega
- Referral tracking and referral earning distribution.
- Promo code support and admin management.
- VPN server provisioning with VLESS link generation.
- Admin tools for managing servers, plans, locations, and user balances.

## Project Structure

- `main.py` — bot startup and dispatcher configuration.
- `config.py` — environment variables and settings loader.
- `db/` — database initialization, models, and CRUD operations.
- `handlers/` — Telegram handlers for bot commands and callbacks.
- `keyboards/` — inline and reply keyboard builders.
- `middlewares/` — request throttling.
- `payments/` — payment gateway integrations.
- `vless/` — VPN link generation and server API interactions.

## Requirements

- Python 3.10+
- `pip`

## Installation

1. Clone the repository.
2. Change into the project directory:
   ```bash
   cd /path/to/unlimitz_vpn_tg_bot/unlimitz_vpn_tg_bot
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the project root and set the following variables:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=your_admin_user_id
PANEL_URL=https://your-vpn-panel.example
USERNAME=panel_username
PASSWORD=panel_password
INBOUND_ID=1
PANEL_USERNAME=admin
PANEL_PASSWORD=admin
CRYPTOBOT_TOKEN=your_cryptopay_token
NOWPAYMENTS_API_KEY=your_nowpayments_api_key
PLATEGA_MERCHANT_ID=your_platega_merchant_id
PLATEGA_SECRET=your_platega_secret
```

Notes:
- `BOT_TOKEN` is required to run the bot.
- `INBOUND_ID` is used by the VPN server provisioning API.
- `PANEL_USERNAME` and `PANEL_PASSWORD` default to `admin` if not set.

## Usage

Run the bot with:

```bash
python main.py
```

The bot will:
- initialize the SQLite database (`db.sqlite3`)
- clear any existing webhook
- start polling for Telegram updates

## Database

The bot uses SQLite as its database backend. The following tables are created automatically:

- `admins`
- `users`
- `subscriptions`
- `plans`
- `locations`
- `plan_prices`
- `servers`
- `referral_settings`
- `referrals`
- `referral_earnings`
- `promo_codes`
- `promo_activations`

## Payment Gateways

The bot includes support for multiple payment channels:

- `payments/crypto.py` — CryptoPay invoice creation and status check.
- `payments/nowpayments.py` — NOWPayments order creation and payment status.
- `payments/platega.py` — Platega invoice creation and transaction checks.

## Customization

To adapt the bot to your VPN service:

- Update the VPN API integration in `vless/api.py`.
- Add or adjust server records in the `servers` table.
- Define plans and locations via database seed data or admin handlers.
- Customize bot text and menus in `handlers/`.

## Notes

- The bot uses `MemoryStorage` for FSM state and does not persist session state across restarts.
- Admin functionality is handled through the database and bot command handlers.

## License

This project does not include a license file.
