import random
import requests
import os
import tempfile
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN!")

REPO_OWNER = "pokify"
REPO_NAME = "poki-art-bot"
BRANCH = "main"
FOLDER_PATH = "folder-images"
TOTAL_IMAGES = 669  # 0 to 668 = 669 files

# Generate correct URL: File_000.png to File_668.png
def get_random_png_url():
    file_num = random.randint(0, TOTAL_IMAGES - 1)  # 0 to 668
    file_name = f"File_{file_num:03d}.png"  # e.g., File_007.png
    raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{file_name}"
    return raw_url

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        img_url = get_random_png_url()
        print(f"Sending GitHub PNG: {img_url}")

        # Download
        img_response = requests.get(img_url, timeout=10)
        if img_response.status_code != 200:
            await update.message.reply_text("Image not found—trying again... 🐹")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_file.write(img_response.content)
            temp_path = temp_file.name

        # Send clean image
        with open(temp_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo)
        
        os.unlink(temp_path)

    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)} 😿")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art from folder-images")
    app.run_polling()

if __name__ == "__main__":
    main()
