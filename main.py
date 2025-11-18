import random
import requests
import os
import tempfile
import urllib.parse
import pickle
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"

# Persistent storage (Railway volume)
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = f"{DATA_DIR}/poki_state.pkl"
CACHE_TTL = 600  # 10 minutes

# Global state
all_files = []
file_cache_time = 0
seen_images = set()

# =============== STATE PERSISTENCE ===============
def load_state():
    global seen_images, all_files, file_cache_time
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                data = pickle.load(f)
                seen_images = set(data.get("seen", []))
                all_files = data.get("files", [])
                file_cache_time = data.get("cache_time", 0)
                print(f"State loaded: {len(seen_images)} seen, {len(all_files)} total images")
        except Exception as e:
            print(f"Failed to load state: {e}")

def save_state():
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump({
                "seen": list(seen_images),
                "files": all_files,
                "cache_time": file_cache_time
            }, f)
    except Exception as e:
        print(f"Failed to save state: {e}")

load_state()

# =============== FETCH ALL IMAGES ===============
def get_all_files():
    global all_files, file_cache_time
    now = time.time()

    # Use cache if fresh
    if all_files and (now - file_cache_time) < CACHE_TTL:
        return all_files

    try:
        # Get latest commit SHA
        commit_resp = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}",
            timeout=10
        )
        commit_resp.raise_for_status()
        commit_sha = commit_resp.json()["sha"]

        # Full recursive tree
        tree_resp = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit_sha}?recursive=1",
            timeout=20
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json()["tree"]

        prefix = f"{FOLDER_PATH}/"
        files = []
        for item in tree:
            if item["type"] == "blob" and item["path"].startswith(prefix):
                name = item["path"][len(prefix):]
                if name.startswith("hamster (") and name.endswith((".png", ".jpg")):
                    files.append(name)

        all_files = files
        file_cache_time = now
        print(f"Refreshed: Found {len(all_files)} hamster images.")
        save_state()
        return all_files

    except Exception as e:
        print(f"Failed to fetch files: {e}")
        return all_files or []

# =============== /art COMMAND ===============
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_all_files()
        if not files:
            await update.message.reply_text("No hamster art found! 🐹")
            return

        # Reset if all seen
        if len(seen_images) >= len(files):
            seen_images.clear()
            print("All images shown — cycle reset!")
            save_state()

        # Random from unseen
        available = [f for f in files if f not in seen_images]
        if not available:
            available = files  # fallback

        chosen = random.choice(available)
        seen_images.add(chosen)
        save_state()

        encoded = urllib.parse.quote(chosen)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"
        print(f"Sending: {url} | Seen: {len(seen_images)}/{len(files)}")

        r = requests.get(url, timeout=15)
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

# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print(f"Poki Art Bot LIVE! {len(get_all_files())} images | Seen: {len(seen_images)}")
    app.run_polling()

if __name__ == "__main__":
    main()