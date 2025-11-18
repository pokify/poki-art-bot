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

# Cache the file list (refresh every 10 minutes)
_file_cache = None
_cache_time = 0
CACHE_TTL = 600

def get_real_files():
    global _file_cache, _cache_time
    now = os.times()[4]
    if _file_cache and (now - _cache_time) < CACHE_TTL:
        return _file_cache

    # Use Git tree API (recursive = no 1000 limit)
    try:
        commit = requests.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}").json()["sha"]
        tree = requests.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit}?recursive=1").json()["tree"]
    except:
        return _file_cache or []

    prefix = f"{FOLDER_PATH}/"
    files = []
    for item in tree:
        if item["type"] == "blob" and item["path"].startswith(prefix):
            name = item["path"][len(prefix):]
            if name.startswith("hamster (") and name.endswith((".png", ".jpg")):
                files.append(name)

    _file_cache = files
    _cache_time = now
    print(f"Found {len(files)} real hamster images.")
    return files

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_real_files()
        if not files:
            await update.message.reply_text("No hamster art found! 🐹")
            return

        chosen = random.choice(files)
        encoded = urllib.parse.quote(chosen)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"
        print(f"Sending: {url}")

        r = requests.get(url, timeout=12)
        r.raise_for_status()

        suffix = os.path.splitext(chosen)[1]
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
    print("Poki Art Bot LIVE! Random from real files in media-uploads/")
    app.run_polling()

if __name__ == "__main__":
    main()