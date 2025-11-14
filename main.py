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

# Cache for 10 mins to avoid rate limits
_file_cache = None
_cache_time = 0
CACHE_TTL = 600

def get_hamster_files():
    global _file_cache, _cache_time
    import time
    now = time.time()

    if _file_cache and (now - _cache_time) < CACHE_TTL:
        return _file_cache

    # GitHub Search API for full list (up to 1,000; query for hamster files)
    search_url = "https://api.github.com/search/code"
    query = f"filename:hamster repo:{REPO_OWNER}/{REPO_NAME} path:media-uploads"
    params = {
        "q": query,
        "per_page": 100,  # Max 100; multiple pages for 1,422
        "page": 1
    }
    headers = {"Accept": "application/vnd.github.v3+json"}

    files = []
    page = 1
    while True:
        params["page"] = page
        resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            break
        data = resp.json()
        if not data['items']:
            break

        for item in data['items']:
            file_name = item['name']
            if file_name.startswith("hamster (") and file_name.endswith((".png", ".jpg")):
                files.append(file_name)

        page += 1

    _file_cache = files
    _cache_time = now
    print(f"Found {len(files)} hamster images via search API.")
    return files

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_hamster_files()
        if not files:
            await update.message.reply_text("No hamster art found! Check folder. 🐹")
            return

        file_name = random.choice(files)
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
