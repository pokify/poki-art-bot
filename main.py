import random
import os
from telethon import TelegramClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === CONFIG (Railway Environment Variables) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "testytestyyo")

# Validate required vars
if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Missing BOT_TOKEN, API_ID, or API_HASH in Railway variables!")

# === TELETHON CLIENT (Uses uploaded poki_session.session) ===
client = TelegramClient('poki_session', API_ID, API_HASH)

# === /art COMMAND ===
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await client.start()  # Uses saved session — no input needed
        photos = [msg.id async for msg in client.iter_messages(SOURCE_CHANNEL, limit=100) if msg.photo]
        if not photos:
            await update.message.reply_text("No art in @testytestyyo yet! Try again later.")
            return
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=f"@{SOURCE_CHANNEL}",
            message_id=random.choice(photos)
        )
    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)}")
    finally:
        await client.disconnect()

# === MAIN BOT SETUP ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot is LIVE! Use /art in any chat.")
    app.run_polling()

if __name__ == "__main__":
    main()
