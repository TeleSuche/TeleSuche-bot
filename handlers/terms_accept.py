# handlers/terms_accept.py

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db
from utils.keyboards import main_menu_keyboard


async def accept_terms(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    db.save_terms_acceptance(user_id)  # ✅ appel corrigé
    lang = db.get_user_language(user_id)  # ✅ appel corrigé

    if lang == 'fr':
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
"""
    else:
        text = """
🤖 <b>TeleSucheBot - Your All-in-One Platform</b>

<b>🔍 Intelligent Search</b>
Instant file indexing

<b>💎 Premium Subscriptions</b>
Automatic payment management

<b>🛠️ Community Management</b>
Advanced moderation tools

<b>🤑 Integrated Monetization</b>
Built-in payment system

<b>🛒 Digital Store</b>
Product/service sales with inventory

<b>🤖 Bot Creation</b>
AI/human support bots

<i>Terms accepted</i>
"""

    await query.edit_message_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
        disable_web_page_preview=True
    )


def setup(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(accept_terms, pattern='^accept_terms$'))
