import random
import requests
import os
import urllib.parse
import pickle
import datetime
import asyncio
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "media-uploads"
MORE_ART_URL = "https://t.me/pokithehammy"
BOT_USERNAME = "PokiArt_Bot"  # @PokiArt_Bot

# Persistent storage
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = f"{DATA_DIR}/poki_state.pkl"

# Global state
all_files = []
seen_images = set()
chat_settings = {}  # chat_id: {"interval": int, "num": int}
last_refresh = None
REFRESH_COOLDOWN_MINUTES = 10

# =============== STATE PERSISTENCE ===============
def load_state():
    global seen_images, chat_settings
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                data = pickle.load(f)
                seen_images = set(data.get("seen", []))
                chat_settings = data.get("settings", {})
            print(f"[{datetime.datetime.now()}] State loaded: {len(seen_images)} seen images, {len(chat_settings)} settings")
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Failed to load state: {e}")

def save_state():
    try:
        with open(STATE_FILE, "wb") as f:
            pickle.dump({"seen": list(seen_images), "settings": chat_settings}, f)
    except Exception as e:
        print(f"[{datetime.datetime.now()}] Failed to save state: {e}")

load_state()

def get_chat_settings(chat_id: int) -> dict:
    return chat_settings.get(chat_id, {"interval": 60, "num": 1})

def save_chat_settings(chat_id: int, interval: int, num: int):
    chat_settings[chat_id] = {"interval": interval, "num": num}
    save_state()

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

# =============== SEND ART HELPER ===============
async def send_random_art(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Send one random unseen art image to a specific chat."""
    files = get_all_files()
    if not files:
        return False

    if len(seen_images) >= len(files):
        seen_images.clear()
        print("Seen list reset (reached end of collection)")
        save_state()

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

        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()

            photo = BytesIO(r.content)
            photo.name = chosen

            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=f'🖼️ <a href="{MORE_ART_URL}"><u>gallery</u></a>',
                parse_mode="HTML"
            )

            seen_images.add(chosen)
            save_state()
            print(f"✅ Sent successfully to {chat_id}: {chosen}")
            return True

        except Exception as e:
            print(f"Attempt {attempt+1} failed for {chosen}: {e}")
            continue

    return False

# =============== /art COMMAND ===============
async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        success = await send_random_art(context, update.effective_chat.id)
        if not success:
            await update.message.reply_text("Defeated by my smolness, try /art again 🐹")
    except Exception as e:
        print(f"Unexpected error in /art: {e}")
        await update.message.reply_text("Defeated by my smolness, try /art again 🐹")

# =============== /artsettings COMMAND ===============
async def delete_config_msg(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    try:
        await context.bot.delete_message(chat_id=job.chat_id, message_id=job.data)
    except Exception:
        pass

async def artsettings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Delete the /artsettings command message immediately
    try:
        await update.message.delete()
    except Exception:
        pass

    # Send Config Artbot with Open button (deep link to bot)
    deep_link = f"https://t.me/{BOT_USERNAME}?start=settings_{chat_id}"
    keyboard = [[InlineKeyboardButton("Open", url=deep_link)]]
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Config Artbot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Delete Config Artbot message after 6 seconds
    context.job_queue.run_once(
        delete_config_msg,
        when=6,
        chat_id=chat_id,
        data=msg.message_id,
        name=f"del_config_{chat_id}_{msg.message_id}"
    )

# =============== SETTINGS UI HELPERS ===============
def get_settings_text(interval_str: str, num: int) -> str:
    display_interval = interval_str if interval_str else "0"
    return (
        "Set auto-art posts\n\n"
        f"Post art every: {display_interval}mins (0 = none)\n"
        f"Number to post: {num}"
    )

def get_settings_keyboard() -> InlineKeyboardMarkup:
    # Number pad for minutes (0-9 + < delete)
    # Using "<" — Telegram handles it fine in button text
    rows = [
        [
            InlineKeyboardButton("1", callback_data="digit_1"),
            InlineKeyboardButton("2", callback_data="digit_2"),
            InlineKeyboardButton("3", callback_data="digit_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="digit_4"),
            InlineKeyboardButton("5", callback_data="digit_5"),
            InlineKeyboardButton("6", callback_data="digit_6"),
        ],
        [
            InlineKeyboardButton("7", callback_data="digit_7"),
            InlineKeyboardButton("8", callback_data="digit_8"),
            InlineKeyboardButton("9", callback_data="digit_9"),
        ],
        [
            InlineKeyboardButton("0", callback_data="digit_0"),
            InlineKeyboardButton("<", callback_data="digit_del"),
        ],
    ]
    # Posts controls: - Posts +
    rows.append([
        InlineKeyboardButton("-", callback_data="post_dec"),
        InlineKeyboardButton("Posts", callback_data="ignore"),
        InlineKeyboardButton("+", callback_data="post_inc"),
    ])
    # Save
    rows.append([InlineKeyboardButton("Save", callback_data="save")])
    return InlineKeyboardMarkup(rows)

async def send_settings_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    interval_str = ud.get("interval_str", "60")
    num = ud.get("num_posts", 1)
    text = get_settings_text(interval_str, num)
    keyboard = get_settings_keyboard()

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)

# =============== /start (deep link for settings) ===============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith("settings_"):
        try:
            target_chat = int(context.args[0].split("_", 1)[1])
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid settings link.")
            return

        settings = get_chat_settings(target_chat)
        context.user_data["target_chat"] = target_chat
        context.user_data["interval_str"] = str(settings["interval"])
        context.user_data["num_posts"] = settings["num"]

        await send_settings_message(update, context)
    else:
        await update.message.reply_text(
            "Hi! I'm Poki Art Bot 🐹\n"
            "Use /art in groups to get hamster art.\n"
            "Use /artsettings in a group to configure auto-art posts."
        )

# =============== SETTINGS CALLBACKS ===============
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ud = context.user_data

    if "target_chat" not in ud:
        await query.edit_message_text("Session expired. Please use /artsettings again from the group.")
        return

    interval_str = ud.get("interval_str", "60")
    num = ud.get("num_posts", 1)

    if data.startswith("digit_"):
        if data == "digit_del":
            interval_str = interval_str[:-1] if interval_str else ""
        else:
            digit = data.split("_", 1)[1]
            if len(interval_str) < 5:  # reasonable limit
                interval_str += digit
        ud["interval_str"] = interval_str

    elif data == "post_inc":
        num = min(num + 1, 10)
        ud["num_posts"] = num

    elif data == "post_dec":
        num = max(num - 1, 1)
        ud["num_posts"] = num

    elif data == "save":
        try:
            interval = int(interval_str) if interval_str else 0
        except ValueError:
            interval = 0

        target_chat = ud["target_chat"]
        save_chat_settings(target_chat, interval, num)

        # Update / reschedule the auto job
        update_auto_job(context.application, target_chat, interval, num)

        await query.edit_message_text(
            f"✅ Settings saved!\n\n"
            f"Post art every: {interval}mins\n"
            f"Number to post: {num}"
        )
        # Clear session
        ud.clear()
        return

    elif data == "ignore":
        return  # do nothing for the "Posts" label button

    # Refresh the settings message
    ud["interval_str"] = interval_str
    ud["num_posts"] = num
    await query.edit_message_text(
        text=get_settings_text(interval_str, num),
        reply_markup=get_settings_keyboard()
    )

# =============== AUTO POST JOB ===============
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    num = job.data.get("num", 1) if job.data else 1

    print(f"[{datetime.datetime.now()}] Auto-posting {num} art(s) to {chat_id}")
    for i in range(num):
        await send_random_art(context, chat_id)
        if i < num - 1:
            await asyncio.sleep(2)  # small delay between posts

def update_auto_job(app: Application, chat_id: int, interval_minutes: int, num: int):
    """Remove old job and schedule new one if interval > 0."""
    job_name = f"auto_{chat_id}"
    # Remove existing jobs for this chat
    for job in app.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()

    if interval_minutes > 0:
        app.job_queue.run_repeating(
            auto_post_job,
            interval=interval_minutes * 60,
            first=interval_minutes * 60,
            chat_id=chat_id,
            name=job_name,
            data={"num": num},
        )
        print(f"Scheduled auto-art for chat {chat_id}: every {interval_minutes}min, {num} posts")
    else:
        print(f"Disabled auto-art for chat {chat_id}")

def schedule_existing_jobs(app: Application):
    """On startup, restore auto jobs from saved settings."""
    for chat_id, settings in chat_settings.items():
        interval = settings.get("interval", 0)
        num = settings.get("num", 1)
        if interval > 0:
            update_auto_job(app, chat_id, interval, num)

# =============== MAIN ===============
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("art", art))
    app.add_handler(CommandHandler("artsettings", artsettings))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(settings_callback))

    # Restore auto jobs
    schedule_existing_jobs(app)

    total = len(get_all_files())
    print(f"\n🚀 Poki Art Bot LIVE! {total} images ready | Seen: {len(seen_images)} | Settings: {len(chat_settings)}\n")

    app.run_polling()

if __name__ == "__main__":
    main()
