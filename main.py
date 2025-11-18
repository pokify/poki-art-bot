import random
import requests
import os
import tempfile
import urllib.parse
import pickle
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"

# Persistent storage now
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
SEEN_FILE = f"{DATA_DIR}/seen_images.pkl"

# Load seen set
def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return set()
    return set()

# Save seen set
def save_seen(seen):
    try:
        with open(SEEN_FILE, "wb") as f:
            pickle.dump(seen, f)
    except:
        pass

seen_images = load_seen()
all_files = []

def get_all_files():
    global all_files
    if all_files:
        return all_files

    # Get latest commit SHA
    try:
        commit = requests.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}").json()
        sha = commit["sha"]
    except:
        return all_files

    # Full tree
    try:
        tree = requests.get(f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{sha}?recursive=1").json()["tree"]
    except:
        return all_files

    prefix = f"{FOLDER_PATH}/"
    files = []
    for item in tree:
        if item["type"] == "blob" and item["path"].startswith(prefix):
            name = item["path"][len(prefix):]
            if name.startswith("hamster (") and name.endswith((".png", ".jpg")):
                files.append(name)

    all_files = files
    print(f"Loaded {len(files)} images.")
    return files

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_all_files()
        if not files:
            await update.message.reply_text("No art found! 🐹")
            return

        # Reset if all seen
        if len(seen_images) >= len(files):
            seen_images.clear()
            save_seen(seen_images)
            print("All images shown — reset!")

        # True random from unseen
        available = [f for f in files if f not in seen_images]
        if not available:
            available = files  # fallback

        chosen = random.choice(available)
        seen_images.add(chosen)
        save_seen(seen_images)

        encoded = urllib.parse.quote(chosen)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"
        print(f"Sending: {url} | Seen: {len(seen_images)}/{len(files)}")

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
    print(f"Poki Art Bot LIVE! {len(get_all_files())} images | Seen: {len(seen_images)}")
    app.run_polling()

if __name__ == "__main__":
    main()