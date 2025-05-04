import json
import logging
import os

from dotenv import load_dotenv
from telegram import ChatMember, Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING)

load_dotenv(dotenv_path = ".token/token.env")
TOKEN = str(os.getenv("TOKEN"))

if not TOKEN:
    raise ValueError("TOKEN must be set in environment variables")

# Check if the request_data.json file exists, if not create it
if not os.path.exists("request_data.json"):
    with open("backup_data.json", "w") as f:
        json.dump({}, f, indent=4)


async def save_data(request_data):
    
    with open("backup_data.json", "w") as f:
        json.dump(request_data, f, indent=4)


async def qg_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The main group for the bot, the admin's group"""
    # Check if the user is an admin
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    if update.effective_user.id in [admin.user.id for admin in admins]:
        with open("request_data.json", "r") as f:
            request_data = json.load(f)
        request_data["qg_group"] = {"id": update.effective_chat.id} 
        await save_data(request_data)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hum, tu n'es pas admin ici 😒. Je veux parler à un patron 👑")
        return

# To avoid inadvertently overwriting a pre-existing configuration
user_stat = {}
async def request_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set up the request source for the channel"""
    # Check if the user is an administrator
    if update.effective_user.id in [admin.user.id for admin in admins]:
        with open("request_data.json", "r") as f:
            request_data = json.load(f)
        request_data[f"{str(update.effective_chat.id)}"] = {"title": update.effective_chat.title,
                                                            "request_channel_id": 0}
        await save_data(request_data)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Veuillez utiliser la commande /request_channel dans le canal qui recuille les demandes")
        return
    # Get the channel ID
    source_channel_id = update.effective_chat.id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello 🤗! I'm zone request manager, I collect zone channel and forward them to you 😉. /help", parse_mode = "Markdown")

if __name__ == '__main__':
    """This is a simple Telegram bot that forwards messages from one channel to another.
    It uses the python-telegram-bot library to interact with the Telegram API."""

    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    application.run_polling()



# Commande pour debuter une configuration
# comment faire la config ?





