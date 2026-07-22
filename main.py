import random
import requests
import os
import urllib.parse
import pickle
import datetime
from io import BytesIO
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
last_refresh = None
REFRESH_COOLDOWN_MINUTES = 10

# =============== STATE PERSISTENCE ===============
def load_state():
    global seen_images
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                data = pickle.load(f)
                seen_images = set(data.get("seen", []))
            print(f"[{datetime.datetime.now()}] State loaded: {len(seen_images)} seen images")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Failed to load state: {e}")

def save_state():
    try:
        with open(STATE_FILE, "wb") as f:
            # Only save the seen list (very small)
            pickle.dump({"seen": list(seen_images)}, f)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Failed to save state: {e}")

load_state()

# =============== FETCH ALL IMAGES (with cooldown) ===============
def get_all_files():
    global all_files, last_refresh
    now = datetime.datetime.now()

    if (last_refresh is None or 
        (now - last_refresh).total_seconds() > REFRESH_COOLDOWN_MINUTES * 60):
        
        print(f"[{now}] 🔄 Refreshing file list from GitHub... (cooldown: {REFRESH_COOLDOWN_MINUTES} min)")
        try:
            commit_sha = requests.get(
                f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}", 
                timeout=10
            ).json()["sha"]
            
            tree = requests.get(
                f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/trees/{commit_sha}?recursive=1", 
                timeout=30
            ).json()["tree"]

            prefix = f"{FOLDER_PATH}/"
            files = []
            for item in tree:
                if item.get("type") == "blob" and item["path"].startswith(prefix):
                    name = item["path"][len(prefix):]
                    if name.startswith("hamster (") and name.endswith((".png", ".jpg", ".gif")):
                        files.append(name)

            all_files = files
            last_refresh = now
            print(f"[{now}] ✅ Refreshed successfully: {len(all_files)} hamster images.")
            return all_files

        except Exception as e:
            print(f"[{now}] ❌ Failed to fetch files: {e}")
            if all_files:
                print(f"[{now}] Using cached list ({len(all_files)} files)")
    else:
        print(f"[{now}] 📦 Using cached list ({len(all_files)} files)")

    return all_files or []

# =============== /art COMMAND ===============
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        files = get_all_files()
        if not files:
            await update.message.reply_text("No hamster art found right now. Try again soon! 🐹")
            return

        if len(seen_images) >= len(files):
            seen_images.clear()
            print("Seen list reset (reached end of collection)")
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

        # Try up to 2 times (silent retry)
        for attempt in range(2):
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()

                # Use in-memory BytesIO → no disk usage
                photo = BytesIO(r.content)
                photo.name = chosen

                await update.message.reply_photo(photo=photo)
                return

            except Exception as e:
                print(f"Attempt {attempt+1} failed for {chosen}: {e}")
                continue

        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")

    except Exception as e:
        print(f"Unexpected error in /art: {e}")
        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")

# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    
    total = len(get_all_files())
    print(f"\n🚀 Poki Art Bot LIVE! {total} images ready | Seen: {len(seen_images)}\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()