from typing import Final
import os
import logging
import boto3
import shutil
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import TelegramError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print('Bot is now starting up...')

S3_BUCKET_NAME: Final = os.getenv('S3_BUCKET_NAME')
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')

API_TOKEN: Final = os.getenv('API_TOKEN')
if not API_TOKEN:
    logger.error("TELEGRAM_API_TOKEN environment variable not set.")
    exit(1)

BOT_HANDLE: Final = os.getenv('BOT_HANDLE')

UPLOADING, ANOTHER_UPLOAD = range(2)

async def initiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'Greetings! I am your Text Recognition Bot powered by AWS Textract.\n'
        'Please upload the image you want to extract text from.'
    )
    return UPLOADING

def extract_text_from_image(s3_bucket: str, s3_key: str) -> str:
    try:
        response = textract_client.detect_document_text(
            Document={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}}
        )
    except Exception as e:
        logger.error(f"Textract error: {e}")
        return ""

    extracted_text = ""
    for item in response.get("Blocks", []):
        if item.get("BlockType") == "LINE":
            extracted_text += item.get("Text", "") + "\n"

    return extracted_text.strip()

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if not update.message.photo:
            await update.message.reply_text("No photo found in the message.")
            return UPLOADING

        photo = update.message.photo[-1]
        file_id = photo.file_id
        file = await context.bot.get_file(file_id)

        photos_dir = "photos"
        os.makedirs(photos_dir, exist_ok=True)
        photo_path = os.path.join(photos_dir, f"{file_id}.jpg")

        await file.download_to_drive(photo_path)
        logger.info(f"Downloaded photo {file_id} to {photo_path}")

        s3_key = f"uploads/{file_id}.jpg"
        s3_client.upload_file(photo_path, S3_BUCKET_NAME, s3_key)
        logger.info(f"Uploaded photo {file_id} to S3 bucket {S3_BUCKET_NAME} as {s3_key}")

        extracted_text = extract_text_from_image(S3_BUCKET_NAME, s3_key)

        if extracted_text:
            await update.message.reply_text(f"Extracted text:\n{extracted_text}")
        else:
            await update.message.reply_text("No text detected in the image.")

    except TelegramError as te:
        logger.error(f"Telegram error: {te}")
        await update.message.reply_text("An error occurred while processing your image.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("An unexpected error occurred while uploading the image.")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)
            logger.info(f"Deleted local photo {photo_path}")

    reply_keyboard = [['Yes', 'No']]
    await update.message.reply_text(
        'Would you like to upload another image?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return ANOTHER_UPLOAD

async def handle_another_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_response = update.message.text.lower()
    
    if user_response == 'yes':
        await update.message.reply_text(
            'Please upload the image you want to extract text from.'
        )
        return UPLOADING
    
    elif user_response == 'no':
        await update.message.reply_text(
            'Thank you! If you need anything else, feel free to type /start.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    else:
        await update.message.reply_text(
            'Please choose a valid option.',
            reply_markup=ReplyKeyboardMarkup(
                [['Yes', 'No']], one_time_keyboard=True, resize_keyboard=True
            ),
        )
        return ANOTHER_UPLOAD

async def log_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    if update and update.message:
        try:
            await update.message.reply_text("An unexpected error occurred. Please try again later.")
        except TelegramError:
            pass  

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        'Operation cancelled. Feel free to start again by typing /start.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main() -> None:
    app = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', initiate_command)],
        states={
            UPLOADING: [MessageHandler(filters.PHOTO, handle_image)],
            ANOTHER_UPLOAD: [MessageHandler(filters.Regex('^(Yes|No)$'), handle_another_upload)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler)
    app.add_error_handler(log_error)
    logger.info('Starting polling...')

    app.run_polling(poll_interval=2)

if __name__ == '__main__':
    main()