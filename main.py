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
FOLDER_PATH = "media-uploads"
TOTAL_IMAGES = 5000  # 1 to 5000

# Generate correct URL: hamster (123).png or .jpg
def get_random_image_url():
    file_num = random.randint(1, TOTAL_IMAGES)
    # Try .png first, then .jpg
    for ext in ['.png', '.jpg']:
        file_name = f"hamster ({file_num}){ext}"
        raw_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/{file_name}"
        if requests.head(raw_url, timeout=5).status_code == 200:
            return raw_url
    return None  # No image found

async def art(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        img_url = get_random_image_url()
        if not img_url:
            await update.message.reply_text("No art found for that number! Trying again... 🐹")
            return

        print(f"Sending: {img_url}")

        # Download
        response = requests.get(img_url, timeout=10)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(img_url)[1]) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # Send image
        with open(tmp_path, 'rb') as photo:
            await update.message.reply_photo(photo=photo)

        os.unlink(tmp_path)

    except Exception as e:
        await update.message.reply_text(f"Art error: {str(e)} 😿")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("art", art))
    print("Poki Art Bot LIVE! Use /art from media-uploads")
    app.run_polling()

if __name__ == "__main__":
    main()
