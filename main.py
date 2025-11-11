import random
import os
from telethon import TelegramClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === USER CONFIG (Telethon - Your Phone Login) ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "testytestyyo")

# === BOT CONFIG (PTB - BotFather Token) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Validate
if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Missing BOT_TOKEN, API_ID, or API_HASH!")

# === TELETHON CLIENT (USER SESSION) ===
client = TelegramClient('poki_session', API_ID, API_HASH)

# === /art COMMAND ===
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await client.start()  # Uses poki_session.session (your user login)

        # Fetch photos as USER
        photos = []
        async for msg in client.iter_messages(SOURCE_CHANNEL, limit=100):
            if msg.photo:
                photos.append(msg)

        if not photos:
            await update.message.reply_text("No art in @testytestyyo yet! Try again later.")
            return

        random_msg = random.choice(photos)

        # Forward via BOT (allowed)
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=random_msg.chat_id,
            message_id=random_msg.id
        )

    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)}")
    finally:
        await client.disconnect()

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot is LIVE! Use /art")
    app.run_polling()

if __name__ == "__main__":
    main()