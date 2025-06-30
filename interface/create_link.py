import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from utils.memory_full import db
from interface.link_preview import ProductPreview
from typing import Dict

class LinkCreationHandler:
    """Gestionnaire de création de liens de paiement avec conversation multi-étapes"""

    # États de la conversation
    NAME, DESCRIPTION, PRICE = range(3)

    @staticmethod
    async def start_link_creation(update: Update, context: CallbackContext) -> int:
        """Démarre le processus de création de lien"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Couldn't delete message: {e}")

        user_id = query.from_user.id
        context.user_data['link_data'] = {}  # Stockage temporaire des données
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📦 Quel est le nom de l'article que vous souhaitez vendre ?"
        )
        return self.NAME

    @staticmethod
    async def handle_name(update: Update, context: CallbackContext) -> int:
        """Reçoit et stocke le nom de l'article"""
        user_id = update.effective_user.id
        context.user_data['link_data']['name'] = update.message.text.strip()
        
        await update.message.reply_text(
            "📝 Envoyez une description courte de l’article (max 200 caractères)"
        )
        return self.DESCRIPTION

    @staticmethod
    async def handle_description(update: Update, context: CallbackContext) -> int:
        """Reçoit la description et demande le prix"""
        user_id = update.effective_user.id
        context.user_data['link_data']['description'] = update.message.text.strip()
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Annuler", callback_data="cancel_link"),
                InlineKeyboardButton("🔙 Retour", callback_data="back_description")
            ]
        ])
        
        await update.message.reply_text(
            "💰 Entrez le prix de vente en chiffres (ex: 19.99) :",
            reply_markup=keyboard
        )
        return self.PRICE

    @staticmethod
    async def back_to_description(update: Update, context: CallbackContext) -> int:
        """Retour à l'étape de description"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception:
            pass
            
        await query.message.reply_text(
            "📝 Envoyez une description courte de l’article (max 200 caractères)"
        )
        return self.DESCRIPTION

    @staticmethod
    async def cancel_creation(update: Update, context: CallbackContext) -> int:
        """Annule la création du lien"""
        query = update.callback_query
        await query.answer()
        
        context.user_data.pop('link_data', None)
        
        try:
            await query.delete_message()
        except Exception:
            pass
            
        await query.message.reply_text("🚫 Création de lien annulée.")
        return ConversationHandler.END

    @staticmethod
    async def handle_price(update: Update, context: CallbackContext) -> int:
        """Finalise la création du lien avec le prix"""
        try:
            price = float(update.message.text)
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Prix invalide. Veuillez entrer un nombre positif (ex: 19.99)")
            return self.PRICE

        user_id = update.effective_user.id
        link_data = context.user_data['link_data']
        link_data['price'] = price
        link_data['currency'] = "EUR"  # Devise par défaut
        
        # Génération du lien final
        link = generate_payment_link(user_id, link_data)
        
        # Affichage de l'aperçu
        await ProductPreview.send_preview(
            update,
            {
                **link_data,
                'photo_file_id': "DEFAULT_PHOTO_ID"  # À remplacer par une image réelle
            },
            view_type='creator'
        )
        
        context.user_data.pop('link_data', None)
        return ConversationHandler.END

    @classmethod
    def get_conversation_handler(cls) -> ConversationHandler:
        """Retourne le gestionnaire de conversation configuré"""
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(cls.start_link_creation, pattern="^create_link$")],
            states={
                cls.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_name)],
                cls.DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_description),
                    CallbackQueryHandler(cls.back_to_description, pattern="^back_description$")
                ],
                cls.PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_price),
                    CallbackQueryHandler(cls.cancel_creation, pattern="^cancel_link$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cls.cancel_creation, pattern="^cancel_link$"),
                MessageHandler(filters.COMMAND, cls.cancel_creation)
            ]
        )

# Utilisation
link_handler = LinkCreationHandler()
application.add_handler(link_handler.get_conversation_handler())