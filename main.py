import json
import logging
import os

from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from telegram.helpers import escape_markdown


# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING)


# Bot token configuration
load_dotenv(dotenv_path = ".token/token.env")
TOKEN = str(os.getenv("TOKEN"))
if not TOKEN:
    raise ValueError("TOKEN must be set in environment variables")

# Data configuration
DATA_FILE = "request_data.json"
if not os.path.exists(DATA_FILE):
    with open("request_data.json", "w") as f:
        json.dump({}, f, indent=4)


class BotManager:
    def __init__(self):
        self.user_stat = {}
    
    async def load_data(self) -> {}:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    
    async def save_data(self, data):
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    
    async def is_admin(self, update, context):
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        return update.effective_user.id in [admin.user.id for admin in admins]

bot_manager = BotManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Hello 🤗! Je suis le gestionnaire des requêtes des chaînes zones."
                                            "Ajouter moi aux différents canaux pour commencer 😉. `/help`",
                                       parse_mode = "Markdown")


async def qg_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The main group for the bot, the admin's group"""
    if not await bot_manager.is_admin(update=update, context=context):
        if update.message:
            await update.message.reply_text(text="❌ Réservée aux administrateurs")
            return
        
    data = await bot_manager.load_data()
    data["qg_group"] = {
        "id": update.effective_chat.id,
        "title": update.effective_chat.title
    }
    await bot_manager.save_data(data)
    if update.message:
        await update.message.reply_text("✅ Groupe QG configuré avec succès")
    

async def setup_request_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup the request channel"""
    if not await bot_manager.is_admin(update, context):
        if update.message:
            await update.message.reply_text(text="❌ Réservée aux administrateurs")
            return
    
    data = await bot_manager.load_data()
    chat_id = str(update.effective_chat.id)

    if f"{update.message.from_user.id}" in bot_manager.user_stat.keys():
        user = bot_manager.user_stat.pop(f"{update.message.from_user.id}")
        if user.get("authorized"):
            data[chat_id] = data.pop(f"temp_{update.message.from_user.id}")
            data[chat_id]["request_title"] = update.effective_chat.title
            data[chat_id]["request_id"] = update.effective_chat.id
            await bot_manager.save_data(data)

            # Notifier QG group
            if data["qg_group"]:
                try:
                    await context.bot.send_message(
                        chat_id=data["qg_group"]["id"],
                        text=f"🔔 Nouvelle configuration:\n"
                            f"Les demandes de: *{escape_markdown(text=update.effective_chat.title, version=2)}* "
                            f"seront transferées vers\n"
                            f"*{escape_markdown(text=data[chat_id]["collect_title"], version=2)}* \n"
                            f"Par *{escape_markdown(text=update.message.from_user.first_name, version=2)}* "
                            rf"\(@{escape_markdown(text=update.message.from_user.username, version=2)}\)",
                        parse_mode="MarkdownV2")
                except Exception as e:
                    logging.error(f"Erreur notification QG: {e}")
        return
    
    data[chat_id] = {
        "request_title": update.effective_chat.title,
        "request_id": chat_id,
        "collect_id": None,
        "collect_title": None
    }
    bot_manager.user_stat[str(update.message.from_user.id)] = {
        "authorized" : True,
        "request_id": chat_id
    }
    
    await bot_manager.save_data(data)
    await update.message.reply_text(
        text=r"📌 Canal des requêtes enregistré\. Utilisez `/collect_channel` "
             "dans le groupe de collecte des requêtes correspondant\n"
             "‼️ Attention si c'est *dans un canal et non un groupe* dans lequel les requêtes sont collectées "
             "alors utiliser `!collect_channel`",
        parse_mode="MarkdownV2")

async def setup_collect_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, from_channel=False):
    """Set up the request collect channel/groupe"""
    data = await bot_manager.load_data()
    collect_chat_id = str(update.effective_chat.id)

    if from_channel:
        for key in data.keys():
            if key != "qg_group":
                if data[key]["collect_id"] is None:
                    data[key].update({
                        "collect_id": collect_chat_id,
                        "collect_title": update.effective_chat.title
                    })
                    await bot_manager.save_data(data)
                    if data["qg_group"]:
                        try:
                            await context.bot.send_message(
                                chat_id=data["qg_group"]["id"],
                                text=f"🔔 Nouvelle configuration:\n"
                                     f"Les demandes de: *{escape_markdown(text=data[key]['request_title'],
                                                                          version=2)}* seront transferées vers\n"
                                     f"*{escape_markdown(text=update.effective_chat.title, version=2)}*",
                                parse_mode="MarkdownV2")
                        except Exception as e:
                            logging.error(f"Erreur notification QG: {e}")
                    break
        return


    if not await bot_manager.is_admin(update, context):
        await update.message.reply_text("❌ Réservé aux administrateurs")
        return

    if str(update.message.from_user.id) in bot_manager.user_stat.keys():
        user = bot_manager.user_stat.pop(f"{update.message.from_user.id}")
        request_chat_id = str(user.get("request_id"))
        if user.get("authorized"):
            data[request_chat_id]["collect_id"] = update.effective_chat.id
            data[request_chat_id]["collect_title"] = update.effective_chat.title
            await bot_manager.save_data(data)

            # Notifier QG group
            if data["qg_group"]:
                try:
                    await context.bot.send_message(
                        chat_id=data["qg_group"]["id"],
                        text=f"🔔 Nouvelle configuration:\n"
                            f"Les demandes de: *{escape_markdown(text=data[request_chat_id]['request_title'],
                                                                 version=2)}* seront transferées vers\n"
                            f"*{escape_markdown(text=update.effective_chat.title, version=2)}*\n"
                            f"Par {escape_markdown(text=update.message.from_user.first_name, version=2)} "
                            rf"\(@{escape_markdown(text=update.message.from_user.username, version=2)}\)",
                        parse_mode="MarkdownV2")
                except Exception as e:
                    logging.error(f"Erreur notification QG: {e}")
        return

    data[f"temp_{update.message.from_user.id}"] = {
        "request_title": None,
        "request_id": None,
        "collect_id": collect_chat_id,
        "collect_title": update.effective_chat.title
    }
    bot_manager.user_stat[str(update.message.from_user.id)] = {
        "authorized": True,
    }

    await bot_manager.save_data(data)
    await update.message.reply_text(
        text="📌 Canal de collecte des requêtes enregistré\n"
             "Utilisez `/request_channel` dans le canal correspondant",
        parse_mode="MarkdownV2")


async def delete_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = await bot_manager.load_data()
    chat_config_to_delete = str(update.effective_chat.id)
    if not chat_config_to_delete in data.keys():
        return

    deleted_config = data.pop(chat_config_to_delete)
    await bot_manager.save_data(data)

    # Notifier QG group
    if data["qg_group"]:
        try:
            await context.bot.send_message(
                chat_id=data["qg_group"]["id"],
                text=f"🔔 Suppression de configuration:\n"
                     f"Les demandes de: *{escape_markdown(text=update.effective_chat.title,version=2)}* "
                     f"*ne seront plus* transferées vers \n"
                     f"*{escape_markdown(text=deleted_config["collect_title"], version=2)}*\n"
                     f"Par {escape_markdown(text=update.message.from_user.first_name, version=2)} " 
                     rf"\(@{escape_markdown(text=update.message.from_user.username, version=2)}\)",
                parse_mode="MarkdownV2")
        except Exception as e:
            logging.error(f"Erreur notification QG: {e}")


async def handle_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return

    data = await bot_manager.load_data()
    chat_id = str(update.effective_chat.id)

    # Vérifier si le message provient d'un canal configuré
    if chat_id not in data.keys():
        return

    channel_data = data[chat_id]
    collect_chat_id = channel_data["collect_id"]

    if not collect_chat_id:
        return

    # Vérifier la présence de #req
    text = update.message.caption if update.message.photo else update.message.text
    if not text or "#req" not in text.lower():
        return

    # Formater le message
    request_text = text.replace("#req", "").strip()
    username = update.message.from_user.username or update.message.from_user.first_name
    message = (f"📬 Nouvelle requête de @{escape_markdown(text=username, version=2)} :\n"
               f"*{escape_markdown(text=request_text, version=2)}*")

    # Envoyer au groupe de collecte
    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=collect_chat_id,
                photo=update.message.photo[-1].file_id,
                caption=message,
                parse_mode="MarkdownV2"
            )
        else:
            await context.bot.send_message(
                chat_id=collect_chat_id,
                text=message,
                parse_mode="MarkdownV2"
            )
    except Exception as e:
        logging.error(f"Erreur lors de l'envoi: {e}")


async def check_command_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_message.text:
        return

    command = update.effective_message.text.lower().strip()
    if command.startswith("!collect_channel"):
        await setup_collect_channel(update=update, context=context, from_channel=True)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass


"""async def register_commands(application):
    commands = [
        BotCommand("start", "Démarrer le bot"),
        BotCommand("qg", "Configurer le groupe QG (admin)"),
        BotCommand("setup_request_channel", "Configurer un canal de requêtes (admin)"),
        BotCommand("setup_collect_group", "Configurer un groupe de collecte (admin)")
    ]
    await application.bot.set_my_commands(commands)"""


if __name__ == '__main__':
    """This is a simple Telegram bot that forwards messages from one channel to another.
    It uses the python-telegram-bot library to interact with the Telegram API."""

    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    request_channel_handler = CommandHandler('request_channel', setup_request_channel)
    collect_channel_handler = CommandHandler('collect_channel', setup_collect_channel)
    delete_config_handler = CommandHandler('delete_config', delete_config)
    qg_group_handler = CommandHandler('qg', qg_group)
    collector_handler = MessageHandler(filters.PHOTO | filters.TEXT, handle_requests)
    # Telegram channel don't handler directly bot command
    channel_handler = MessageHandler(
        filters.ChatType.CHANNEL
        & filters.TEXT
        & ~filters.FORWARDED
        & ~filters.IS_AUTOMATIC_FORWARD,
        check_command_for_channel
    )

    application.add_handler(start_handler)
    application.add_handler(request_channel_handler)
    application.add_handler(collect_channel_handler)
    application.add_handler(delete_config_handler)
    application.add_handler(qg_group_handler)
    application.add_handler(channel_handler)
    application.add_handler(collector_handler)
    
    application.run_polling()