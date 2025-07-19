from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Application
from telegram.error import TimedOut
from utils.memory_full import db
from handlers.language import start_language_selection
from utils.menu_utils import show_main_menu
import asyncio
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    try:
        if db.is_new_user(user_id):
            await start_language_selection(update, context)
        else:
            await show_main_menu(update, context)
    except TimedOut:
        logger.warning("Timeout détecté dans la commande /start, réessai...")
        await asyncio.sleep(2)
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Erreur dans la commande start: {e}")
        if update.message:
            await update.message.reply_text("❌ Une erreur s'est produite. Veuillez réessayer.")

def setup(application: Application) -> None:
    application.add_handler(CommandHandler("start", start))