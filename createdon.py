from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)
from typing import Dict, Optional
from utils.memory_full import db
import logging

logger = logging.getLogger(__name__)

class DonationManager:
    """Gestionnaire de création de liens de don avec conversation guidée"""

    # États de la conversation
    LABEL, AMOUNT, BUTTON = range(3)

    @staticmethod
    async def start_donation(update: Update, context: CallbackContext) -> int:
        """Démarre le processus de création de don"""
        user_id = update.effective_user.id
        db.clear_donation(user_id)
        
        await update.message.reply_text(
            "🙏 Quel est l'objet de la collecte ?\n\n"
            "Action :",
            reply_markup=DonationManager._get_navigation_keyboard()
        )
        return self.LABEL

    @staticmethod
    async def handle_label(update: Update, context: CallbackContext) -> int:
        """Reçoit le libellé du don"""
        user_id = update.effective_user.id
        db.save_donation(user_id, "label", update.message.text.strip())
        
        await update.message.reply_text(
            "💰 Montant suggéré (ex: 5.00) ou tapez '0' pour libre :\n\n"
            "Action :",
            reply_markup=DonationManager._get_navigation_keyboard()
        )
        return self.AMOUNT

    @staticmethod
    async def handle_amount(update: Update, context: CallbackContext) -> int:
        """Reçoit le montant du don"""
        user_id = update.effective_user.id
        amount = update.message.text.strip()
        
        try:
            if amount != "0":
                float(amount)  # Validation du format
        except ValueError:
            await update.message.reply_text(
                "❌ Format invalide. Utilisez un nombre (ex: 5.00) ou '0' pour libre"
            )
            return self.AMOUNT
            
        db.save_donation(user_id, "amount", amount)
        
        await update.message.reply_text(
            "🖊️ Texte du bouton (ex: 💙 Faire un don) :\n\n"
            "Action :",
            reply_markup=DonationManager._get_navigation_keyboard()
        )
        return self.BUTTON

    @staticmethod
    async def handle_button(update: Update, context: CallbackContext) -> int:
        """Finalise la création du don"""
        user_id = update.effective_user.id
        db.save_donation(user_id, "button", update.message.text.strip())
        
        data = db.get_donation(user_id)
        label = data.get("label", "Collecte de dons")
        amount = data.get("amount", "0")
        button_text = data.get("button", "💙 Faire un don")
        price = f"{amount} $" if amount != "0" else "libre"

        text = (
            f"🎯 <b>{label}</b>\n"
            f"💸 Montant : {price}\n"
            "Merci pour votre générosité !"
        )

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, url="https://pay.don.example")]
        ])

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=markup
        )
        return ConversationHandler.END

    @staticmethod
    async def cancel_donation(update: Update, context: CallbackContext) -> int:
        """Annule la création du don"""
        user_id = update.effective_user.id
        db.clear_donation(user_id)
        
        await update.message.reply_text("❌ Création de don annulée.")
        return ConversationHandler.END

    @staticmethod
    async def back_to_previous_step(update: Update, context: CallbackContext) -> int:
        """Retour à l'étape précédente"""
        query = update.callback_query
        await query.answer()
        
        current_state = db.get_user_state(query.from_user.id)
        
        if current_state == "don_amount":
            db.set_user_state(query.from_user.id, "don_label")
            await query.edit_message_text(
                "🙏 Quel est l'objet de la collecte ?\n\n"
                "Action :",
                reply_markup=DonationManager._get_navigation_keyboard()
            )
            return self.LABEL
        elif current_state == "don_button":
            db.set_user_state(query.from_user.id, "don_amount")
            await query.edit_message_text(
                "💰 Montant suggéré (ex: 5.00) ou tapez '0' pour libre :\n\n"
                "Action :",
                reply_markup=DonationManager._get_navigation_keyboard()
            )
            return self.AMOUNT

    @staticmethod
    def _get_navigation_keyboard() -> InlineKeyboardMarkup:
        """Retourne le clavier de navigation standard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ Annuler", callback_data="cancel_don"),
                InlineKeyboardButton("🔙 Retour", callback_data="back_don")
            ]
        ])

    @classmethod
    def get_conversation_handler(cls) -> ConversationHandler:
        """Retourne le gestionnaire de conversation configuré"""
        return ConversationHandler(
            entry_points=[CommandHandler("createdon", cls.start_donation)],
            states={
                cls.LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_label)],
                cls.AMOUNT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_amount),
                    CallbackQueryHandler(cls.back_to_previous_step, pattern="^back_don$")
                ],
                cls.BUTTON: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, cls.handle_button),
                    CallbackQueryHandler(cls.back_to_previous_step, pattern="^back_don$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cls.cancel_donation, pattern="^cancel_don$"),
                MessageHandler(filters.COMMAND, cls.cancel_donation)
            ]
        )

# Supprimez ou mettez en commentaire ces deux lignes :
# donation_handler = DonationManager()
# application.add_handler(donation_handler.get_conversation_handler())

# Ajoutez cette fonction à la place :
def register_createdon(application):
    """Enregistre le gestionnaire de conversation pour la création de dons."""
    donation_handler = DonationManager()
    handler = donation_handler.get_conversation_handler()
    application.add_handler(handler)
