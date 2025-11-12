import random
import requests
import os
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN in Railway variables!")

# 10 recent X image URLs from @pokithehamster/media (verified loading)
IMAGE_URLS = [
    "https://pbs.twimg.com/media/G4mltWdWIAAqh9T.jpg",  # treat or treat
    "https://pbs.twimg.com/media/G4hXWoFWMAAB9hN.jpg",  # new friend
    "https://pbs.twimg.com/media/G4b1XKzXkAAJtQ_.jpg",  # big dreams on @bonk_fun
    "https://pbs.twimg.com/media/G34E64vWIAAkzzl.jpg",  # hamster super cycle
    "https://pbs.twimg.com/media/G4SAYWwWQAAbObv.jpg",  # yummy poki
    "https://pbs.twimg.com/media/G4fxIIeXIAAsCVP.jpg",  # oh there is (reply)
    "https://pbs.twimg.com/media/G4IgilQWAAA_8he.jpg",  # https://t.co/LWMvOyNH4V
    "https://pbs.twimg.com/media/G3zPWfFWgAIemaE.jpg",  # New flex just dropped
    "https://pbs.twimg.com/media/G3zPWfLWsAA4nVn.jpg",  # New flex just dropped (2nd)
    "https://pbs.twimg.com/media/G3yihgDXEAAjkzd.jpg"   # mind your step
]

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        img_url = random.choice(IMAGE_URLS)
        print(f"Sending X art: {img_url}")

        # Download to temp file
        img_response = requests.get(img_url, timeout=10)
        img_response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(img_response.content)
            temp_path = temp_file.name

        # Send clean image (no caption)
        with open(temp_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo)
        
        # Clean up
        os.unlink(temp_path)

    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)} 😿")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art")
    app.run_polling()

if __name__ == "__main__":
    main()