import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from typing import Dict, List, Tuple

class CreditManager:
    """Gestionnaire d'achat de crédits avec options configurables"""
    
    CREDIT_PACKS = [
        (50, 2.99, "https://pay.example.com/pack50"),
        (250, 9.99, "https://pay.example.com/pack250"), 
        (1000, 19.99, "https://pay.example.com/pack1000")
    ]

    @classmethod
    def _generate_payment_buttons(cls) -> List[List[InlineKeyboardButton]]:
        """Génère les boutons d'achat dynamiquement"""
        return [
            [InlineKeyboardButton(
                f"💳 Acheter {amount} crédits ({price}$)",
                url=url
            )]
            for amount, price, url in cls.CREDIT_PACKS
        ]

    @classmethod
    async def show_credit_options(cls, update: Update, context: CallbackContext) -> None:
        """Affiche les options d'achat de crédits"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Couldn't delete message: {e}")

        text = (
            "⚡ <b>Ajouter des crédits à votre bot</b>\n\n"
            "💰 Choisissez un pack pour augmenter le nombre de recherches disponibles :\n\n"
            "\n".join(
                f"🔹 {amount} crédits — {price}$"
                for amount, price, _ in cls.CREDIT_PACKS
            ) + 
            "\n\n🛒 Paiement sécurisé via lien personnalisé"
        )

        buttons = cls._generate_payment_buttons()
        buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="go_back")])

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

def setup_credit_handlers(application):
    """Configure les handlers pour l'achat de crédits"""
    application.add_handler(
        CallbackQueryHandler(
            CreditManager.show_credit_options,
            pattern="^add_credits$"
        )
    )