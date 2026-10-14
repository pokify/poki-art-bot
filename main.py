import random
import requests
import os
import urllib.parse
import pickle
import datetime
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
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

# =============== ART SENDING ===============
async def send_art_to_chat(bot, chat_id, count=1):
    """Send up to count artwork images to a Telegram chat."""
    sent = 0
    for _ in range(max(1, int(count))):
        files = await asyncio.to_thread(get_all_files)
        if not files:
            print("No artwork files available.")
            break
        if len(seen_images) >= len(files):
            seen_images.clear()
            save_state()
        available = [f for f in files if f not in seen_images]
        if not available:
            seen_images.clear()
            available = list(files)
        random.shuffle(available)
        delivered = False
        for chosen in available[:min(10, len(available))]:
            encoded = urllib.parse.quote(chosen)
            url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{encoded}"
            try:
                r = await asyncio.to_thread(requests.get, url, timeout=15)
                r.raise_for_status()
                photo = BytesIO(r.content)
                photo.name = chosen
                await bot.send_photo(
                    chat_id=chat_id, photo=photo,
                    caption=f'🖼️ <a href="{MORE_ART_URL}"><u>gallery</u></a>',
                    parse_mode="HTML")
                seen_images.add(chosen)
                save_state()
                sent += 1
                delivered = True
                print(f"Art sent to {chat_id}: {chosen}")
                break
            except Exception as e:
                print(f"Failed sending {chosen} to {chat_id}: {e}")
        if not delivered:
            break
    return sent

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sent = await send_art_to_chat(context.bot, update.effective_chat.id, 1)
        if not sent and update.effective_message:
            await update.effective_message.reply_text("Couldn't send art right now. Please try again.")
    except Exception as e:
        print(f"Unexpected error in /art: {e}")
        if update.effective_message:
            await update.effective_message.reply_text("Couldn't send art right now. Please try again.")

# =============== ART SETTINGS ===============
SETTINGS_FILE = f"{DATA_DIR}/art_settings.pkl"
art_settings = {"minutes": "60", "posts": 1, "chat_id": None}
def load_art_settings():
    global art_settings
    try:
        with open(SETTINGS_FILE, "rb") as f:
            art_settings.update(pickle.load(f))
        art_settings["minutes"] = str(art_settings.get("minutes", "60"))
        art_settings["posts"] = max(1, min(20, int(art_settings.get("posts", 1))))
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
    text = (f"Set auto-art posts\n\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\nNumber to post: {art_settings['posts']}")
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
        "open", url=f"https://t.me/PokiArt_Bot?start=artsettings_{update.effective_chat.id}")]])
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
    if context.args and context.args[0].startswith("artsettings"):
        payload = context.args[0]
        parts = payload.split("_", 1)
        if len(parts) == 2:
            try:
                art_settings["chat_id"] = int(parts[1])
            except ValueError:
                art_settings["chat_id"] = update.effective_chat.id
        else:
            art_settings["chat_id"] = update.effective_chat.id
        save_art_settings()
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
            f"Set auto-art posts\n\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:+":
        art_settings["posts"] = min(20, int(art_settings["posts"]) + 1)
        await q.edit_message_text(
            f"Set auto-art posts\n\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:-":
        art_settings["posts"] = max(1, int(art_settings["posts"]) - 1)
        await q.edit_message_text(
            f"Set auto-art posts\n\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\nNumber to post: {art_settings['posts']}", reply_markup=settings_keyboard())
    elif data == "artposts:show":
        pass
    elif data == "artsave":
        save_art_settings()
        if settings_changed is not None:
            settings_changed.set()
        await q.edit_message_text(
            f"Saved!\n\nPost art every: {art_settings['minutes']}mins (0 = none)"
            f"\nNumber to post: {art_settings['posts']}")



async def auto_art_loop(app):
    """Post artwork on the configured interval; settings saves wake the loop immediately."""
    print("Auto-art scheduler started")
    while True:
        try:
            minutes = max(0, int(str(art_settings.get("minutes", "60")) or "0"))
            if minutes == 0:
                if settings_changed is not None:
                    settings_changed.clear()
                    await settings_changed.wait()
                else:
                    await asyncio.sleep(30)
                continue
            if settings_changed is not None:
                settings_changed.clear()
                try:
                    await asyncio.wait_for(settings_changed.wait(), timeout=minutes * 60)
                    continue  # configuration changed; recalculate interval
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(minutes * 60)
            # Re-read settings after waiting, so disabling/changing the interval takes effect.
            minutes = max(0, int(str(art_settings.get("minutes", "60")) or "0"))
            if minutes == 0:
                continue
            chat_id = art_settings.get("chat_id")
            if not chat_id:
                print("Auto-art skipped: no destination chat configured. Open /artsettings from the target chat.")
                continue
            count = max(1, min(20, int(art_settings.get("posts", 1))))
            print(f"Auto-art triggered: {count} post(s) to {chat_id}")
            await send_art_to_chat(app.bot, chat_id, count)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Auto-art scheduler error: {e}")
            await asyncio.sleep(5)

async def post_init(app):
    global settings_changed
    settings_changed = asyncio.Event()
    app.create_task(auto_art_loop(app), name="auto_art_loop")

    # Register commands so they appear in the Telegram menu
    # Group chats: show /art and /artsettings with the requested description
    await app.bot.set_my_commands(
        commands=[
            BotCommand("art", "Get random Poki art"),
            BotCommand("artsettings", "art bot settings"),
        ],
        scope=BotCommandScopeAllGroupChats()
    )
    # Private chats as well for consistency
    await app.bot.set_my_commands(
        commands=[
            BotCommand("art", "Get random Poki art"),
            BotCommand("artsettings", "art bot settings"),
            BotCommand("start", "Start the bot"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )


# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("art", art))
    app.add_handler(CommandHandler("artsettings", artsettings))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(art_settings_callback, pattern=r"^(artdigit:|artposts:|artsave)"))
    
    total = len(get_all_files())
    print(f"\n🚀 Poki Art Bot LIVE! {total} images ready | Seen: {len(seen_images)}\n")
    
    app.run_polling()

if __name__ == "__main__":
    main()