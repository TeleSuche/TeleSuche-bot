from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackContext,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)
from typing import Dict, Optional
from utils.memory_full import db
from utils.currency_selector import CurrencySelector, setup_currency_handlers
from interface.store_preview import StorePreview
import logging

logger = logging.getLogger(__name__)

class StoreCreationManager:
    """Gestionnaire complet de création de boutique avec conversation multi-étapes"""

    # États de la conversation
    NAME, DESCRIPTION, PRICE, CURRENCY, PHOTO, DELIVERY = range(6)

    @staticmethod
    async def start_creation(update: Update, context: CallbackContext) -> int:
        """Démarre le processus de création"""
        user_id = update.effective_user.id
        db.clear_store_data(user_id)
        
        await update.message.reply_text("🛍️ Quel est le nom de votre produit ?")
        return StoreCreationManager.NAME

    @staticmethod
    async def handle_name(update: Update, context: CallbackContext) -> int:
        """Traite le nom du produit"""
        user_id = update.effective_user.id
        db.save_store_data(user_id, "name", update.message.text.strip())
        
        await update.message.reply_text("📝 Envoyez une description courte du produit")
        return StoreCreationManager.DESCRIPTION

    @staticmethod
    async def handle_description(update: Update, context: CallbackContext) -> int:
        """Traite la description du produit"""
        user_id = update.effective_user.id
        db.save_store_data(user_id, "description", update.message.text.strip())
        
        await update.message.reply_text(
            "💰 Entrez le prix de vente en chiffres (ex: 19.99) :",
            reply_markup=StoreCreationManager._get_navigation_keyboard("price")
        )
        return StoreCreationManager.PRICE

    @staticmethod
    async def handle_price(update: Update, context: CallbackContext) -> int:
        """Valide et stocke le prix"""
        try:
            price = float(update.message.text)
            if price <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "❌ Prix invalide. Veuillez entrer un nombre positif (ex: 19.99)",
                reply_markup=StoreCreationManager._get_navigation_keyboard("price")
            )
            return StoreCreationManager.PRICE

        user_id = update.effective_user.id
        db.save_store_data(user_id, "price", str(price))
        
        await update.message.reply_text(
            "💱 Choisissez une devise :",
            reply_markup=CurrencySelector.get_currency_markup()
        )
        return StoreCreationManager.CURRENCY

    @staticmethod
    async def handle_currency(update: Update, context: CallbackContext) -> int:
        """Traite la sélection de devise"""
        query = update.callback_query
        await query.answer()
        
        currency = query.data.split("_")[1]
        user_id = query.from_user.id
        db.save_store_data(user_id, "currency", currency)
        
        await query.edit_message_text("🖼️ Envoyez une photo du produit")
        return StoreCreationManager.PHOTO

    @staticmethod
    async def handle_photo(update: Update, context: CallbackContext) -> int:
        """Traite la photo du produit"""
        user_id = update.effective_user.id
        photo_id = update.message.photo[-1].file_id
        db.save_store_data(user_id, "photo", photo_id)
        
        await update.message.reply_text(
            "🚚 Quel mode de paiement souhaitez-vous activer ?",
            reply_markup=StoreCreationManager._get_delivery_keyboard()
        )
        return StoreCreationManager.DELIVERY

    @staticmethod
    async def handle_delivery(update: Update, context: CallbackContext) -> int:
        """Finalise la création avec le mode de livraison"""
        query = update.callback_query
        await query.answer()
        
        mode = query.data.split("_")[1]
        user_id = query.from_user.id
        db.save_store_data(user_id, "delivery_mode", mode)
        
        await query.delete_message()
        await StorePreview.send(update, user_id)
        return ConversationHandler.END

    @staticmethod
    async def back_to_previous(update: Update, context: CallbackContext) -> Optional[int]:
        """Gère la navigation vers l'étape précédente"""
        query = update.callback_query
        await query.answer()
        
        target = query.data.split("_")[-1]
        
        if target == "name":
            await query.edit_message_text("🛍️ Quel est le nom de votre produit ?")
            return StoreCreationManager.NAME
        elif target == "description":
            await query.edit_message_text("📝 Envoyez une description courte du produit")
            return StoreCreationManager.DESCRIPTION
        elif target == "price":
            await query.edit_message_text(
                "💰 Entrez le prix de vente en chiffres (ex: 19.99) :",
                reply_markup=StoreCreationManager._get_navigation_keyboard("price")
            )
            return StoreCreationManager.PRICE

    @staticmethod
    async def cancel_creation(update: Update, context: CallbackContext) -> int:
        """Annule le processus de création"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        db.clear_store_data(user_id)
        
        await query.edit_message_text("❌ Création de boutique annulée.")
        return ConversationHandler.END

    @staticmethod
    def _get_navigation_keyboard(target_step: str) -> InlineKeyboardMarkup:
        """Génère le clavier de navigation standard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Annuler", callback_data="cancel_store"),
                InlineKeyboardButton("🔙 Retour", callback_data=f"store_back_{target_step}")
            ]
        ])

    @staticmethod
    def _get_delivery_keyboard() -> InlineKeyboardMarkup:
        """Génère le clavier de sélection du mode de livraison"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💳 Paiement en ligne", callback_data="delivery_online"),
                InlineKeyboardButton("💵 Paiement à la livraison", callback_data="delivery_cash")
            ],
            [InlineKeyboardButton("❌ Annuler", callback_data="cancel_store")]
        ])

    @classmethod
    def get_conversation_handler(cls) -> ConversationHandler:
        """Retourne le gestionnaire de conversation configuré"""
        return ConversationHandler(
            entry_points=[CommandHandler("addstore", cls.start_creation)],
            states={
                cls.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_name)],
                cls.DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_description),
                    CallbackQueryHandler(cls.back_to_previous, pattern="^store_back_name$")
                ],
                cls.PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_price),
                    CallbackQueryHandler(cls.back_to_previous, pattern="^store_back_description$")
                ],
                cls.CURRENCY: [
                    CallbackQueryHandler(cls.handle_currency, pattern="^currency_"),
                    CallbackQueryHandler(cls.back_to_previous, pattern="^store_back_price$")
                ],
                cls.PHOTO: [
                    MessageHandler(filters.PHOTO, cls.handle_photo),
                    CallbackQueryHandler(cls.back_to_previous, pattern="^store_back_currency$")
                ],
                cls.DELIVERY: [
                    CallbackQueryHandler(cls.handle_delivery, pattern="^delivery_"),
                    CallbackQueryHandler(cls.cancel_creation, pattern="^cancel_store$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cls.cancel_creation, pattern="^cancel_store$"),
                MessageHandler(filters.COMMAND, cls.cancel_creation)
            ]
        )

def register_addstore(application: Application):
    """Enregistre les handlers de création de boutique"""
    store_creator = StoreCreationManager()
    application.add_handler(store_creator.get_conversation_handler())
    setup_currency_handlers(application)