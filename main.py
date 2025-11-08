import random, re, requests, os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
DEPOT_URL = "https://memedepot.com/d/pokithehamster"
IMAGE_BASE = "https://memedepot.com/i/"

async def poki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(DEPOT_URL, timeout=10)
        r.raise_for_status()
        images = re.findall(r'(Hamster_gallery_\d+(?:-2)?\.png|Poki_carousel[^"]*\.png)', r.text)
        if not images:
            await update.message.reply_text("No Poki art found! Try again later. 🐹")
            return
        img = random.choice(images)
        await update.message.reply_photo(
            photo=IMAGE_BASE + img,
            caption="Fresh Poki art! 🐹"
        )
    except Exception as e:
        await update.message.reply_text(f"Art error: {e} 😿")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("poki", poki))
    print("Poki Art Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
