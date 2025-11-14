import random
import requests
import os
import tempfile
import urllib.parse
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"

# Cache file list to avoid API spam (refresh every 5 mins)
_file_cache = None
_cache_time = 0
CACHE_TTL = 300  # 5 minutes

def get_hamster_files():
    global _file_cache, _cache_time
    now = os.times()[4]  # uptime in seconds

    if _file_cache and (now - _cache_time) < CACHE_TTL:
        return _file_cache

    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FOLDER_PATH}?ref={BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        resp.raise_for_status()
        files = resp.json()

        # Filter: starts with "hamster (" and ends with .png or .jpg
        hamster_files = [
            f for f in files
            if f["name"].startswith("hamster (") and f["name"].endswith((".png", ".jpg"))
        ]

        _file_cache = hamster_files
        _cache_time = now
        print(f"Found {len(hamster_files)} hamster images.")
        return hamster_files

    except Exception as e:
        print(f"GitHub API error: {e}")
        return _file_cache or []  # fallback to cache

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_hamster_files()
        if not files:
            await update.message.reply_text("No hamster art found! Check folder. 🐹")
            return

        file = random.choice(files)
        file_name = file["name"]
        encoded_name = urllib.parse.quote(file_name)
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded_name}"

        print(f"Sending: {raw_url}")

        img_resp = requests.get(raw_url, timeout=12)
        img_resp.raise_for_status()

        suffix = os.path.splitext(file_name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(img_resp.content)
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
    print("Poki Art Bot LIVE! Pulling from media-uploads/")
    app.run_polling()

if __name__ == "__main__":
    main()
