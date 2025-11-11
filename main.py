import random
import os
from telethon import TelegramClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === SAFE CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "testytestyyo")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Missing BOT_TOKEN, API_ID, or API_HASH in environment!")

API_ID = int(API_ID)  # Now safe to convert
# =========================

client = TelegramClient('session', API_ID, API_HASH)

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await client.start()
        photos = [msg.id async for msg in client.iter_messages(SOURCE_CHANNEL, limit=100) if msg.photo]
        if not photos:
            await update.message.reply_text("No art yet! 🐹")
            return
        await context.bot.forward_message(update.effective_chat.id, f"@{SOURCE_CHANNEL}", random.choice(photos))
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        await client.disconnect()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art")
    app.run_polling()

if __name__ == "__main__":
    main()