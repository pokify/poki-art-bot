import random
import requests
import os
import tempfile
import urllib.parse
import pickle
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

# Persistent storage
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = f"{DATA_DIR}/poki_state.pkl"

# Global state
all_files = []
seen_images = set()

# =============== STATE PERSISTENCE ===============
def load_state():
    global seen_images, all_files
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                data = pickle.load(f)
                seen_images = set(data.get("seen", []))
                all_files = data.get("files", [])
        except:
            pass

def save_state():
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"seen": list(seen_images), "files": all_files}, f)
    except:
        pass

load_state()

# =============== FETCH ALL IMAGES ===============
def get_all_files():
    global all_files
    if all_files:
        return all_files

    try:
        commit_sha = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}", 
            timeout=10
        ).json()["sha"]
        
        tree = requests.get(
            f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit_sha}?recursive=1", 
            timeout=20
        ).json()["tree"]

        prefix = f"{FOLDER_PATH}/"
        files = []
        for item in tree:
            if item.get("type") == "blob" and item["path"].startswith(prefix):
                name = item["path"][len(prefix):]
                if name.startswith("hamster (") and name.endswith((".png", ".jpg", ".gif")):
                    files.append(name)

        all_files = files
        print(f"Refreshed: Found {len(all_files)} hamster images.")
        save_state()
        return all_files

    except Exception as e:
        print(f"Failed to fetch files: {e}")
        return all_files or []

# =============== /art COMMAND (Normal random) ===============
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_all_files()
        if not files:
            await update.message.reply_text("No hamster art found right now. Try again soon! 🐹")
            return

        if len(seen_images) >= len(files):
            seen_images.clear()
            save_state()

        available = [f for f in files if f not in seen_images]
        if not available:
            available = files

        chosen = random.choice(available)
        seen_images.add(chosen)
        save_state()

        encoded = urllib.parse.quote(chosen)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"

        print(f"Sending: {chosen} | Seen: {len(seen_images)}/{len(files)}")

        r = requests.get(url, timeout=15)
        r.raise_for_status()

        suffix = os.path.splitext(chosen)[1] or ".jpg"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(r.content)
        tmp_path = tmp.name
        tmp.close()

        with open(tmp_path, "rb") as file:
            if chosen.endswith(".gif"):
                await update.message.reply_animation(animation=file)
            else:
                await update.message.reply_photo(photo=file)

        os.unlink(tmp_path)

    except Exception as e:
        print(f"Art error: {e}")
        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")

# =============== /test COMMAND (Specific GIF) ===============
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file_name = "hamster (1360).gif"
        encoded = urllib.parse.quote(file_name)
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"

        print(f"/test command - Sending specific GIF: {file_name}")

        r = requests.get(url, timeout=15)
        r.raise_for_status()

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
        tmp.write(r.content)
        tmp_path = tmp.name
        tmp.close()

        with open(tmp_path, "rb") as file:
            await update.message.reply_animation(animation=file)

        os.unlink(tmp_path)

    except Exception as e:
        print(f"/test error: {e}")
        await update.message.reply_text("Could not load the test GIF. Try again later! 🐹")

# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    app.add_handler(CommandHandler("test", test))   # ← New command
    total = len(get_all_files())
    print(f"Poki Art Bot LIVE! {total} images ready | Seen: {len(seen_images)}")
    app.run_polling()

if __name__ == "__main__":
    main()