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

# Persistent storage
DATA_DIR = "/data"
SEEN_FILE = f"{DATA_DIR}/seen_images.pkl"
INDEX_FILE = f"{DATA_DIR}/image_index.pkl"

# Ensure /data exists
os.makedirs(DATA_DIR, exist_ok=True)

# Load or initialize seen images and index
def load_state():
    seen = set()
    index = 0
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "rb") as f:
                data = pickle.load(f)
                seen = data.get("seen", set())
        except:
            pass
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "rb") as f:
                index = pickle.load(f).get("index", 0)
        except:
            pass
    return seen, index

def save_state(seen, index):
    try:
        with open(SEEN_FILE, "wb") as f:
            pickle.dump({"seen": seen}, f)
        with open(INDEX_FILE, "wb") as f:
            pickle.dump({"index": index}, f)
    except:
        pass  # Best effort

seen_images, current_index = load_state()
all_files = []

def get_all_files():
    global all_files
    if all_files:
        return all_files

    # Get latest commit
    try:
        commit_resp = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}",
            timeout=10
        )
        commit_resp.raise_for_status()
        commit_sha = commit_resp.json()["sha"]
    except:
        return all_files

    # Full recursive tree
    try:
        tree_resp = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit_sha}?recursive=1",
            timeout=15
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json()["tree"]
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
    print(f"Loaded {len(all_files)} hamster images.")
    return files

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_index, seen_images, all_files

    try:
        files = get_all_files()
        if not files:
            await update.message.reply_text("No hamster art found! Check media-uploads/. Hamster")
            return

        # Reset if all seen
        if len(seen_images) >= len(files):
            seen_images = set()
            current_index = 0
            save_state(seen_images, current_index)
            print("All images shown — reset cycle!")

        # Pick next in sequence
        while True:
            file_name = files[current_index]
            current_index = (current_index + 1) % len(files)
            if file_name not in seen_images:
                break

        seen_images.add(file_name)
        save_state(seen_images, current_index)

        encoded = urllib.parse.quote(file_name)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"

        print(f"Sending: {url} | Progress: {len(seen_images)}/{len(files)}")

        r = requests.get(url, timeout=12)
        r.raise_for_status()

        suffix = os.path.splitext(file_name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(r.content)
        tmp_path = tmp.name
        tmp.close()

        with open(tmp_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)

        os.unlink(tmp_path)

    except Exception as e:
        await update.message.reply_text(f"Art error: {e} Hamster")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print(f"Poki Art Bot LIVE! No repeats until all {len(get_all_files())} seen.")
    app.run_polling()

if __name__ == "__main__":
    main()