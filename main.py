import random
import requests
import os
import tempfile
import urllib.parse
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------------------------------------
# 1. Prevent double polling
LOCK_FILE = "/tmp/bot.lock"
if os.path.exists(LOCK_FILE):
    print("Another instance is running – exiting.")
    sys.exit(0)
open(LOCK_FILE, "w").close()
# -------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME  = "poki-art-bot"
BRANCH     = "main"
FOLDER     = "media-uploads"
MAX_NUM    = 5000                     # 1 … 5000

def random_image_url() -> str | None:
    num = random.randint(1, MAX_NUM)
    for ext in (".png", ".jpg"):
        name = f"hamster ({num}){ext}"
        enc  = urllib.parse.quote(name)                # ← %20 for space
        url  = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER}/{enc}"
        if requests.head(url, timeout=5).status_code == 200:
            return url
    return None

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = random_image_url()
        if not url:
            await update.message.reply_text("No art found for that number – trying again… 🐹")
            return

        print(f"Sending → {url}")
        r = requests.get(url, timeout=12)
        r.raise_for_status()

        suffix = os.path.splitext(url)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(r.content)
        tmp_path = tmp.name
        tmp.close()

        with open(tmp_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)

        os.unlink(tmp_path)

    except Exception as e:
        await update.message.reply_text(f"Art error: {e} 😿")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art from media-uploads")
    app.run_polling()

if __name__ == "__main__":
    main()
