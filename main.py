import random
import requests
import os
import tempfile
import urllib.parse
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"

# Cache
_file_cache = None
_cache_time = 0
CACHE_TTL = 600  # 10 mins

def get_all_files_in_folder():
    global _file_cache, _cache_time
    now = time.time()
    if _file_cache and (now - _cache_time) < CACHE_TTL:
        return _file_cache

    # Get latest commit SHA
    commits_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
    commit_resp = requests.get(commits_url, timeout=10)
    commit_resp.raise_for_status()
    commit_sha = commit_resp.json()["sha"]

    # Get tree
    tree_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit_sha}?recursive=1"
    tree_resp = requests.get(tree_url, timeout=15)
    tree_resp.raise_for_status()
    tree = tree_resp.json()["tree"]

    # Filter: in media-uploads/, starts with hamster (, ends with .png/.jpg
    files = []
    prefix = f"{FOLDER_PATH}/"
    for item in tree:
        if item["type"] == "blob" and item["path"].startswith(prefix):
            name = item["path"][len(prefix):]
            if name.startswith("hamster (") and name.endswith((".png", ".jpg")):
                files.append(name)

    _file_cache = files
    _cache_time = now
    print(f"Found {len(files)} hamster images (full tree scan).")
    return files

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_all_files_in_folder()
        if not files:
            await update.message.reply_text("No hamster art found! Check media-uploads/. 🐹")
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
    print("Poki Art Bot LIVE! Full scan of media-uploads/")
    app.run_polling()

if __name__ == "__main__":
    main()
