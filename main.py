import random
import os
from telethon import TelegramClient
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === USER CLIENT (Telethon - Phone Session) ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "testytestyyo")

# === BOT (PTB - BotFather Token) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([BOT_TOKEN, API_ID, API_HASH]):
    raise ValueError("Missing env vars!")

# Telethon as USER client (poki_session.session)
user_client = TelegramClient('poki_session', API_ID, API_HASH)

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await user_client.start()  # User session - full history access

        # Fetch photos as USER (allowed)
        photos = []
        async for msg in user_client.iter_messages(SOURCE_CHANNEL, limit=100):
            if msg.photo:
                photos.append(msg)

        if not photos:
            await update.message.reply_text("No art in @testytestyyo yet! 🐹")
            return

        random_msg = random.choice(photos)

        # Forward as BOT (allowed for known messages)
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=random_msg.peer_id.channel_id,
            message_id=random_msg.id
        )

    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)}")
    finally:
        await user_client.disconnect()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art")
    app.run_polling()

if __name__ == "__main__":
    main()
