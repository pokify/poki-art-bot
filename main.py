import random
import requests
import os
import urllib.parse
import pickle
import datetime
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"
MORE_ART_URL = "https://t.me/pokithehammy"

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

        # Try up to 3 different images
        max_attempts = 3
        tried = set()

        for attempt in range(max_attempts):
            available = [f for f in files if f not in seen_images and f not in tried]
            if not available:
                available = [f for f in files if f not in tried]
            if not available:
                break

            chosen = random.choice(available)
            tried.add(chosen)

            encoded = urllib.parse.quote(chosen)
            url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"

            print(f"Trying: {chosen} | Attempt {attempt+1}/{max_attempts} | Seen: {len(seen_images)}/{len(files)}")

            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()

                photo = BytesIO(r.content)
                photo.name = chosen

                await update.message.reply_photo(
                    photo=photo,
                    caption=f'🖼️ <a href="{MORE_ART_URL}"><u>gallery</u></a>',
                    parse_mode="HTML"
                )

                # Only mark as seen AFTER successful send
                seen_images.add(chosen)
                save_state()
                print(f"✅ Sent successfully: {chosen}")
                return

            except Exception as e:
                print(f"Attempt {attempt+1} failed for {chosen}: {e}")
                continue

        # All attempts failed
        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")

    except Exception as e:
        print(f"Unexpected error in /art: {e}")
        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")


# =============== ART SETTINGS ===============
SETTINGS_FILE = f"{DATA_DIR}/art_settings.pkl"
art_settings = {"minutes": "60", "posts": 1}
def load_art_settings():
    global art_settings
    try:
        with open(SETTINGS_FILE, "rb") as f:
            art_settings.update(pickle.load(f))
    except Exception:
        pass

def save_art_settings():
    with open(SETTINGS_FILE, "wb") as f:
        pickle.dump(art_settings, f)

load_art_settings()

def settings_keyboard():
    minutes = art_settings["minutes"] or "0"
    rows = [
        [InlineKeyboardButton(ch, callback_data=f"artdigit:{ch}") for ch in "123"],
        [InlineKeyboardButton(ch, callback_data=f"artdigit:{ch}") for ch in "456"],
        [InlineKeyboardButton(ch, callback_data=f"artdigit:{ch}") for ch in "789"],
        [InlineKeyboardButton("0", callback_data="artdigit:0"),
         InlineKeyboardButton("⌫", callback_data="artdigit:del")],
        [InlineKeyboardButton("−", callback_data="artposts:-"),
         InlineKeyboardButton(f"No of Posts: {art_settings['posts']}", callback_data="artposts:show"),
         InlineKeyboardButton("+", callback_data="artposts:+")],
        [InlineKeyboardButton("Save", callback_data="artsave")]
    ]
    return InlineKeyboardMarkup(rows)

async def show_settings(update, context):
    text = (f"Set auto-art posts\\n\\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\\nNumber to post: {art_settings['posts']}")
    if update.message:
        await update.message.reply_text(text, reply_markup=settings_keyboard())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=settings_keyboard())

async def artsettings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Remove the slash command immediately, then show a temporary launch prompt.
    try:
        await update.message.delete()
    except Exception:
        pass
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(
        "open", url="https://t.me/PokiArt_Bot?start=artsettings")]])
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Config Artbot", reply_markup=keyboard)
    async def remove_prompt():
        await asyncio.sleep(6)
        try:
            await msg.delete()
        except Exception:
            pass
    asyncio.create_task(remove_prompt())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == "artsettings":
        await show_settings(update, context)

async def art_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data.startswith("artdigit:"):
        value = data.split(":", 1)[1]
        current = str(art_settings["minutes"])
        if value == "del":
            current = current[:-1]
        elif len(current) < 4:
            current = ("" if current == "0" else current) + value
        art_settings["minutes"] = current or "0"
        await q.edit_message_text(
            f"Set auto-art posts\\n\\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:+":
        art_settings["posts"] = min(20, int(art_settings["posts"]) + 1)
        await q.edit_message_text(
            f"Set auto-art posts\\n\\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:-":
        art_settings["posts"] = max(1, int(art_settings["posts"]) - 1)
        await q.edit_message_text(
            f"Set auto-art posts\\n\\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:show":
        pass
    elif data == "artsave":
        save_art_settings()
        await q.edit_message_text(
            f"Saved!\\n\\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\\nNumber to post: {art_settings['posts']}")


# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    app.add_handler(CommandHandler("artsettings", artsettings))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(art_settings_callback, pattern=r"^(artdigit:|artposts:|artsave)"))
    
    total = len(get_all_files())
    print(f"\n🚀 Poki Art Bot LIVE! {total} images ready | Seen: {len(seen_images)}\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()