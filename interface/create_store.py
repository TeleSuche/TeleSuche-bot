import logging
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from typing import Dict

class StoreCreationHandler:
    """Gestionnaire de création de boutique avec conversation multi-étapes"""

    # États de la conversation
    AWAITING_NAME, AWAITING_DESC, AWAITING_ITEMS = range(3)

    def __init__(self):
        self.user_data: Dict[int, Dict] = {}

    async def start_store_creation(self, update: Update, context: CallbackContext) -> int:
        """Démarre le processus de création de boutique"""
        query = update.callback_query
        await query.answer()

        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Couldn't delete message: {e}")

        user_id = update.effective_user.id
        self.user_data[user_id] = {}  # Initialise le stockage temporaire

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🛒 Commençons la création de votre boutique !\n\n"
                 "Veuillez d'abord envoyer le <b>nom de votre boutique</b> :",
            parse_mode="HTML"
        )
        return self.AWAITING_NAME

    async def handle_store_name(self, update: Update, context: CallbackContext) -> int:
        """Reçoit et stocke le nom de la boutique"""
        user_id = update.effective_user.id
        self.user_data[user_id]['name'] = update.message.text

        await update.message.reply_text(
            "📝 Excellent ! Maintenant, envoyez une <b>description</b> pour votre boutique :",
            parse_mode="HTML"
        )
        return self.AWAITING_DESC

    async def handle_store_description(self, update: Update, context: CallbackContext) -> int:
        """Reçoit la description et demande les articles"""
        user_id = update.effective_user.id
        self.user_data[user_id]['description'] = update.message.text

        await update.message.reply_text(
            "🛍️ Parfait ! Maintenant, envoyez vos <b>articles</b> (un par ligne) "
            "avec le format : <code>Nom|Prix|Description</code>\n\n"
            "Exemple :\n"
            "<code>T-shirt|19.99|T-shirt en coton bio</code>\n"
            "<code>Casquette|12.50|Casquette ajustable</code>\n\n"
            "Envoyez <code>/done</code> quand vous avez terminé.",
            parse_mode="HTML"
        )
        return self.AWAITING_ITEMS

    async def handle_store_items(self, update: Update, context: CallbackContext) -> int:
        """Traite les articles de la boutique"""
        user_id = update.effective_user.id
        
        if 'items' not in self.user_data[user_id]:
            self.user_data[user_id]['items'] = []

        try:
            name, price, desc = update.message.text.split('|', 2)
            self.user_data[user_id]['items'].append({
                'name': name.strip(),
                'price': float(price.strip()),
                'description': desc.strip()
            })
            await update.message.reply_text("✅ Article ajouté !")
        except Exception as e:
            await update.message.reply_text(
                "❌ Format incorrect. Utilisez : <code>Nom|Prix|Description</code>",
                parse_mode="HTML"
            )

        return self.AWAITING_ITEMS

    async def complete_store_creation(self, update: Update, context: CallbackContext) -> int:
        """Finalise la création de la boutique"""
        user_id = update.effective_user.id
        store_data = self.user_data.pop(user_id, {})

        # Ici vous pourriez sauvegarder store_data dans votre base de données
        response = (
            "🏪 <b>Boutique créée avec succès !</b>\n\n"
            f"<b>Nom :</b> {store_data.get('name', 'N/A')}\n"
            f"<b>Description :</b> {store_data.get('description', 'N/A')}\n"
            f"<b>Articles :</b> {len(store_data.get('items', []))}\n\n"
            "Utilisez /manage_store pour modifier votre boutique."
        )

        await update.message.reply_text(response, parse_mode="HTML")
        return ConversationHandler.END

    async def cancel_creation(self, update: Update, context: CallbackContext) -> int:
        """Annule la création de la boutique"""
        user_id = update.effective_user.id
        self.user_data.pop(user_id, None)

        await update.message.reply_text("❌ Création de boutique annulée.")
        return ConversationHandler.END

    def get_conversation_handler(self) -> ConversationHandler:
        """Retourne le gestionnaire de conversation configuré"""
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_store_creation, pattern="^create_store$")],
            states={
                self.AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_store_name)],
                self.AWAITING_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_store_description)],
                self.AWAITING_ITEMS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_store_items),
                    MessageHandler(filters.Regex(r'^/done$'), self.complete_store_creation)
                ]
            },
            fallbacks=[
                MessageHandler(filters.Regex(r'^/cancel$'), self.cancel_creation),
                MessageHandler(filters.COMMAND, self.cancel_creation)
            ]
        )

# Utilisation
store_handler = StoreCreationHandler()
application.add_handler(store_handler.get_conversation_handler())