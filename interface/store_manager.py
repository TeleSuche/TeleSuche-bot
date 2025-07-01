import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db

logger = logging.getLogger(__name__)

class StoreManager:
    """Gestionnaire complet de modification de boutique avec menu interactif"""

    @staticmethod
    async def show_edit_menu(update: Update, context: CallbackContext) -> None:
        """Affiche le menu de modification du produit"""
        query = update.callback_query
        await query.answer()

        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Impossible de supprimer le message: {e}")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Modifier le nom", callback_data="edit_name")],
            [InlineKeyboardButton("📝 Modifier la description", callback_data="edit_description")],
            [InlineKeyboardButton("💰 Modifier le prix", callback_data="edit_price")],
            [InlineKeyboardButton("💱 Modifier la devise", callback_data="edit_currency")],
            [InlineKeyboardButton("🖼️ Modifier l'image", callback_data="edit_photo")],
            [InlineKeyboardButton("❌ Supprimer", callback_data="confirm_delete")],
            [InlineKeyboardButton("🔙 Retour", callback_data="preview_store")]
        ])

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⚙️ Modifier votre produit :",
            reply_markup=keyboard
        )

    @staticmethod
    async def confirm_deletion(update: Update, context: CallbackContext) -> None:
        """Demande confirmation avant suppression"""
        query = update.callback_query
        await query.answer()

        confirmation_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Confirmer suppression", callback_data="delete_product")],
            [InlineKeyboardButton("🔙 Annuler", callback_data="store_edit")]
        ])

        await query.edit_message_text(
            "⚠️ Êtes-vous sûr de vouloir supprimer ce produit ?",
            reply_markup=confirmation_keyboard
        )

    @staticmethod
    async def delete_product(update: Update, context: CallbackContext) -> None:
        """Supprime définitivement le produit"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        db.clear_store_data(user_id)

        try:
            await query.delete_message()
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🗑️ Produit supprimé avec succès."
        )

    @staticmethod
    async def return_to_preview(update: Update, context: CallbackContext) -> None:
        """Retourne à l'aperçu du produit"""
        query = update.callback_query
        await query.answer()

        try:
            await query.delete_message()
        except Exception:
            pass

        # Solution temporaire si StorePreview n'est pas disponible
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔙 Retour à l'aperçu du produit"
        )

def register_store_manager(application):
    """Configure les handlers de gestion de boutique"""
    application.add_handler(CallbackQueryHandler(
        StoreManager.show_edit_menu,
        pattern="^store_edit$"
    ))
    application.add_handler(CallbackQueryHandler(
        StoreManager.confirm_deletion,
        pattern="^confirm_delete$"
    ))
    application.add_handler(CallbackQueryHandler(
        StoreManager.delete_product,
        pattern="^delete_product$"
    ))
    application.add_handler(CallbackQueryHandler(
        StoreManager.return_to_preview,
        pattern="^preview_store$"
    ))