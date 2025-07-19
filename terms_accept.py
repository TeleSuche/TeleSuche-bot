# handlers/terms_accept.py

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db
from utils.menu_utils import show_main_menu

async def accept_terms(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    db.save_terms_acceptance(user_id)
    lang = db.get_user_language(user_id)

    # Appel direct au menu principal après acceptation
    await show_main_menu(update, context)

def setup(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(accept_terms, pattern='^accept_terms$'))