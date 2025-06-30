from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from typing import List, Dict
from utils.memory_full import db
import logging

logger = logging.getLogger(__name__)

class UserHistoryManager:
    """Gestionnaire d'historique utilisateur avec pagination et enrichissement"""

    ITEMS_PER_PAGE = 10

    @classmethod
    async def show_history(cls, update: Update, context: CallbackContext) -> None:
        """Affiche l'historique des actions utilisateur"""
        user_id = update.effective_user.id
        history = db.get_user_history(user_id)

        if not history:
            await update.message.reply_text("🕓 Aucun historique disponible.")
            return

        # Formater les entrées d'historique
        formatted_entries = cls._format_history_entries(history[-cls.ITEMS_PER_PAGE:])
        credits = db.get_user_credits(user_id)

        response = (
            "📚 <b>Historique de vos recherches et actions</b> :\n"
            f"{formatted_entries}\n\n"
            f"🎟️ <b>Crédits restants :</b> {credits}"
        )

        await update.message.reply_text(response, parse_mode="HTML")

    @staticmethod
    def _format_history_entries(entries: List[Dict]) -> str:
        """Formate les entrées d'historique pour l'affichage"""
        return "\n".join(
            f"{i}. {cls._format_history_item(item)}"
            for i, item in enumerate(entries, 1)
        )

    @staticmethod
    def _format_history_item(item: Dict) -> str:
        """Formate une entrée individuelle d'historique"""
        status = "✅" if item.get("downloaded") else "❌"
        return f"🔍 <b>{item['query']}</b> — {status} ({item.get('date', 'date inconnue')})"

# Remplacer la dernière fonction par 

def register_user_history(application):
    """Configure les handlers pour l'historique utilisateur"""
    application.add_handler(CommandHandler("history", UserHistoryManager.show_history))
