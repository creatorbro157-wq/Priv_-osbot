import asyncio
import logging
import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "9197553923:AAGffy-jwmjG00-qh1GE_Iz74GR_dQWRqtk")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7970770278"))
API_BASE_URL = os.getenv("API_BASE_URL", "https://sher-osint-india-num-info.vercel.app/api")
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Flask keep-alive server for Render & UptimeRobot
flask_app = Flask(__name__)


@flask_app.route("/")
@flask_app.route("/health")
def health_check():
    return "Bot is running 24/7!", 200


def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)


def format_api_response(data: dict, fallback_number: str) -> str:
    if not isinstance(data, dict) or data.get("success") is False:
        msg = data.get("message") if isinstance(data, dict) else "No record found."
        return f"❌ *Result Not Found*\nNumber: `{fallback_number}`\nReason: {msg}"

    details = data.get("number_detail") if isinstance(data.get("number_detail"), dict) else data
    num = data.get("number") or details.get("number") or fallback_number

    lines = [f"✅ *Lookup Result for* `{num}`\n"]

    field_labels = [
        ("name", "👤 Name"),
        ("father_name", "👨 Father Name"),
        ("operator", "📡 Operator"),
        ("circle", "🌐 Circle"),
        ("email", "✉️ Email"),
        ("alternate_number", "📞 Alternate No."),
        ("village_city", "🏙️ City/Village"),
        ("district", "🗺️ District"),
        ("state", "📍 State"),
        ("pincode", "📮 Pincode"),
        ("landmark", "🏢 Landmark"),
        ("full_address", "🏠 Full Address"),
    ]

    shown_any = False
    for key, label in field_labels:
        val = details.get(key)
        if val not in (None, "", "null"):
            lines.append(f"*{label}:* `{val}`")
            shown_any = True

    if not shown_any:
        lines.append("```json\n" + str(data)[:3500] + "\n```")

    return "\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Namaste {user.first_name}! 👋\n\n"
        "Kisi bhi mobile number ki detail check karne ke liye *10-digit number* bhejein.",
        parse_mode="Markdown",
    )


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = (update.message.text or "").strip()
    cleaned_number = "".join(ch for ch in raw_text if ch.isdigit())

    if len(cleaned_number) < 10:
        await update.message.reply_text("⚠️ Kripya sahi mobile number bhejein (kam se kam 10 digits).")
        return

    base_url = API_BASE_URL.strip()
    if not base_url:
        await update.message.reply_text(
            "⚠️ `API_BASE_URL` set nahi hai. Kripya Render Environment Variables ya `bot.py` mein apna HTTP JSON API URL set karein.",
            parse_mode="Markdown",
        )
        return

    status_msg = await update.message.reply_text("🔍 API se data fetch ho raha hai...")

    try:
        sep = "&" if "?" in base_url else "?"
        target_url = f"{base_url}{sep}number={cleaned_number}"
        resp = requests.get(target_url, timeout=15)
        resp.raise_for_status()

        try:
            payload = resp.json()
            reply_text = format_api_response(payload, cleaned_number)
        except ValueError:
            reply_text = f"📄 *API Response:*\n```\n{resp.text[:3500]}\n```"

        await status_msg.edit_text(reply_text, parse_mode="Markdown")

    except requests.RequestException as exc:
        logger.error("API error: %s", exc)
        await status_msg.edit_text("❌ API se connect karne mein error aaya. Thodi der baad try karein.")


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    threading.Thread(target=run_flask, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    logger.info("Starting Telegram bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
