#!/usr/bin/env python

import os
import logging
import urllib3
import requests
import urllib.parse as urlparse
from requests.exceptions import HTTPError, MissingSchema, JSONDecodeError
from anonupload import download
from anonupload.main import detect_filename, remove_file

from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
)

urllib3.disable_warnings()

# Enable logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
# )

logger = logging.getLogger(__name__)

UPLOAD, DOWNLOAD = range(2)

download_path = 'downloads'
if not os.path.isdir(download_path):
    os.mkdir(download_path)

async def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(),
    )

async def upload(update: Update, context: CallbackContext):
    """Starts the conversation and asks the user for url"""
    await update.message.reply_text("Enter your url :- ")

    return UPLOAD


async def change_filename(update: Update, context: CallbackContext):
    """Stores the selected url and asks for change file."""
    user = update.message.from_user
    url = update.message.text
    try:
        r_name = requests.get(url, stream=True)
    except MissingSchema:
        await update.message.reply_text("worng url")
        return ConversationHandler.END
    filename = detect_filename(url, r_name.headers)
    context.user_data["filename"] = filename
    context.user_data["url"] = url
    await update.message.reply_text(
        f'Default filename is , "{filename[0:90]}", If you want to chnage filename'
        'enter new filename, or send /skip if you don\'t want to.',
    )
    return DOWNLOAD


def file_remover(filename: str):
    if os.path.isfile(filename):
        os.remove(filename)
    else:
         print("file not found.")


async def fdownload(update: Update, context: CallbackContext):
    """download file and upload file with given name"""
    user = update.message.from_user
    filename = update.message.text
    url = context.user_data.get("url", 'Not found')
    msg = await update.message.reply_text("Downloading file...")
    f_msg = download(url, filename, download_path, True)
    await msg.edit_text(f"File uploaded:\nFull url : {f_msg}")

    return ConversationHandler.END


async def skip_download(update: Update, context: CallbackContext):
    """Skip change file name, download and upload file with async default name"""
    user = update.message.from_user
    url = context.user_data.get("url", 'Not found')
    filename = context.user_data.get("filename", "Not found")
    msg = await update.message.reply_text("Downloading file...")
    f_msg = download(url, filename, download_path, True)
    await msg.edit_text(f"File uploaded:\nFull url : {f_msg}")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    file_server_path = context.user_data.get('file_server_path', 'Not found')
    if file_server_path != 'Not found':
        remove_file(file_server_path)
    await update.message.reply_text(
        'Bye! I hope we can talk again some day.'
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    application = Application.builder().token("Token").build()

    application.add_handler(CommandHandler("start", start))

    # Add conversation handler with the states UPLOAD and DOWNLOAD
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('upload', upload)],
        states={
            UPLOAD: [MessageHandler(filters.Entity('url') | filters.Document.ALL, change_filename)],
            DOWNLOAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, fdownload), CommandHandler('skip', skip_download)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C

    application.run_polling()


if __name__ == '__main__':
    main()