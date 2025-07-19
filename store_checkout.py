from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from utils.memory_full import db
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class StoreCheckoutManager:
    """Gestionnaire complet du processus de commande avec validation"""

    # États de la conversation
    AWAITING_CONTACT, AWAITING_CONFIRMATION = range(2)

    @staticmethod
    async def initiate_checkout(update: Update, context: CallbackContext) -> int:
        """Démarre le processus de commande"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        delivery_mode = db.get_store_data(user_id).get("delivery_mode")

        if delivery_mode == "cash":
            markup = ReplyKeyboardMarkup(
                [
                    [
                        KeyboardButton("📍 Envoyer ma localisation", request_location=True),
                        KeyboardButton("📞 Envoyer mon téléphone", request_contact=True)
                    ]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await query.message.reply_text(
                "💬 Veuillez partager vos coordonnées pour la livraison :",
                reply_markup=markup
            )
            return self.AWAITING_CONTACT
        else:
            return await confirm_order(update, context)

    @staticmethod
    async def handle_location(update: Update, context: CallbackContext) -> int:
        """Traite la localisation partagée"""
        loc = update.message.location
        db.save_order_info(
            update.effective_user.id,
            "location",
            f"{loc.latitude},{loc.longitude}"
        )
        
        await update.message.reply_text(
            "📍 Localisation enregistrée ✅\n"
            "Veuillez maintenant confirmer votre commande :",
            reply_markup=StoreCheckoutManager._get_confirmation_keyboard()
        )
        return self.AWAITING_CONFIRMATION

    @staticmethod
    async def handle_contact(update: Update, context: CallbackContext) -> int:
        """Traite le contact partagé"""
        phone = update.message.contact.phone_number
        db.save_order_info(update.effective_user.id, "phone", phone)
        
        await update.message.reply_text(
            "📞 Numéro enregistré ✅\n"
            "Veuillez maintenant confirmer votre commande :",
            reply_markup=StoreCheckoutManager._get_confirmation_keyboard()
        )
        return self.AWAITING_CONFIRMATION

    @staticmethod
    async def confirm_order(update: Update, context: CallbackContext) -> int:
        """Finalise la commande"""
        user_id = update.effective_user.id
        
        # Ici vous pourriez traiter le paiement et créer la commande
        order_id = process_payment(user_id)  # À implémenter
        
        await update.message.reply_text(
            "🧾 Commande confirmée ✅\n\n"
            f"Votre numéro de commande : {order_id}\n"
            "Vous recevrez un message avec les détails de livraison.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Envoyer le reçu au vendeur
        await send_order_to_seller(context.bot, user_id)  # À implémenter
        
        return ConversationHandler.END

    @staticmethod
    def _get_confirmation_keyboard() -> ReplyKeyboardMarkup:
        """Génère le clavier de confirmation"""
        return ReplyKeyboardMarkup(
            [[KeyboardButton("✅ Confirmer la commande")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @classmethod
    def get_conversation_handler(cls) -> ConversationHandler:
        """Retourne le gestionnaire de conversation configuré"""
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(
                cls.initiate_checkout,
                pattern="^buy_now$"
            )],
            states={
                cls.AWAITING_CONTACT: [
                    MessageHandler(filters.LOCATION, cls.handle_location),
                    MessageHandler(filters.CONTACT, cls.handle_contact)
                ],
                cls.AWAITING_CONFIRMATION: [
                    MessageHandler(
                        filters.Regex(r'^✅ Confirmer') & ~filters.COMMAND,
                        cls.confirm_order
                    )
                ]
            },
            fallbacks=[]
        )

# Fonctions utilitaires (à implémenter selon votre logique métier)
def process_payment(user_id: int) -> str:
    """Traite le paiement et retourne un ID de commande"""
    # Implémentez votre logique de paiement ici
    return f"CMD-{user_id[:6]}"

async def send_order_to_seller(bot, user_id: int):
    """Envoie les détails de la commande au vendeur"""
    order_data = db.get_order_info(user_id)
    store_data = db.get_store_data(user_id)
    
    # Construisez et envoyez le message au vendeur
    # ...

def register_store_checkout(application):
    """Enregistre le gestionnaire de conversation pour le checkout."""
    handler = StoreCheckoutManager.get_conversation_handler()
    application.add_handler(handler)

# Supprimez l'ancienne ligne :
# application.add_handler(StoreCheckoutManager.get_conversation_handler())
