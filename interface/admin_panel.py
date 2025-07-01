import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler

logger = logging.getLogger(__name__)

async def show_admin_panel(update: Update, context: CallbackContext):
    """Affiche le panneau d'administration avec les options de gestion"""
    query = update.callback_query
    await query.answer()

    try:
        await query.delete_message()
    except Exception as e:
        logger.debug(f"Could not delete message: {e}")

    text = (
        "<b>👑 Panneau Administrateur</b>\n\n"
        "Personnalisez votre bot fils et gérez vos paramètres.\n"
        "Sélectionnez une des options ci-dessous :"
    )

    keyboard = [
        [InlineKeyboardButton("🎨 Modifier nom", callback_data="edit_name"),
         InlineKeyboardButton("🖼️ Modifier photo", callback_data="edit_photo")],
        [InlineKeyboardButton("📊 Voir statistiques", callback_data="view_stats"),
         InlineKeyboardButton("🎯 Gestion crédits", callback_data="credit_management")],
        [InlineKeyboardButton("🔍 Paramètres recherche", callback_data="search_settings"),
         InlineKeyboardButton("📌 Commandes bot", callback_data="edit_commands")],
        [InlineKeyboardButton("🔑 Clé API", callback_data="generate_apikey"),
         InlineKeyboardButton("🛠️ Paramètres avancés", callback_data="advanced_settings")],
        [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
    ]

    await context.bot.send_message(
        chat_id=query.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def setup_admin_handlers(application):
    """Enregistre les handlers pour le panneau admin"""
    application.add_handler(
        CallbackQueryHandler(
            show_admin_panel,
            pattern="^admin_panel$"
        )
    )
    # Ajouter ici d'autres handlers admin si nécessaire