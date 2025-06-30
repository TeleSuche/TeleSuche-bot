from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Application
from utils.memory_full import db
from utils.keyboards import main_menu_keyboard
from handlers.language import start_language_selection


async def start(update: Update, context: CallbackContext) -> None:
    """Handler for the /start command."""
    user_id = update.effective_user.id

    if db.is_new_user(user_id):
        await start_language_selection(update, context)
    else:
        await show_main_menu(update, context)


async def show_main_menu(update: Update, context: CallbackContext) -> None:
    """Displays the main menu with user's language preference."""
    user_id = update.effective_user.id
    lang = db.get_user_language(user_id)

    # Texte principal en fonction de la langue
    text = """
🤖 <b>TeleSucheBot - Votre plateforme tout-en-un</b>

<b>🔍 Recherche Intelligente</b>
Indexation instantanée de tous vos fichiers et médias

<b>💎 Abonnements Premium</b>
Gestion automatique des abonnements payants

<b>🛠️ Gestion de Communauté</b>
Outils de modération avancés

<b>🤑 Monétisation Intégrée</b>
Système de paiement intégré

<b>🛒 Boutique Digitale</b>
Vente de produits/services avec gestion de stocks

<b>🤖 Création de Bot Assistant</b>
Bots support IA/humain

<i>Conditions d'utilisation acceptées</i>
""" if lang == 'fr' else """
🤖 <b>TeleSucheBot - Your All-in-One Platform</b>

<b>🔍 Intelligent Search</b>
Instant indexing of all your files and media

<b>💎 Premium Subscriptions</b>
Automatic management of paid subscriptions

<b>🛠️ Community Management</b>
Advanced moderation tools

<b>🤑 Integrated Monetization</b>
Integrated payment system

<b>🛒 Digital Store</b>
Product/service sales with stock management

<b>🤖 Bot Assistant Creation</b>
AI/Human supported bots

<i>Terms of use accepted</i>
"""

    reply_method = (
        update.callback_query.edit_message_text if update.callback_query
        else update.message.reply_text
    )

    await reply_method(
        text=text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    if update.callback_query:
        await update.callback_query.answer()


def setup(application: Application) -> None:
    """Sets up the command handlers."""
    application.add_handler(CommandHandler("start", start))