import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext
from typing import Dict, Any
from utils.memory_full import db
import logging

logger = logging.getLogger(__name__)

class AdminStatsManager:
    """Gestionnaire des statistiques administrateur avec protection d'accès"""

    @staticmethod
    async def handle_stats(update: Update, context: CallbackContext) -> None:
        """Affiche les statistiques administrateur"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            await update.message.reply_text(
                "❌ Accès refusé. Cette commande est réservée aux administrateurs."
            )
            return

        stats = db.get_bot_stats(user_id)
        if not stats:
            await update.message.reply_text("📊 Aucune statistique trouvée pour l’instant.")
            return

        text = (
            "📈 <b>Statistiques globales</b>\n\n"
            f"🛒 Ventes : {stats.get('sales', 0)}\n"
            f"💰 Revenus : {stats.get('revenue', 0)} $\n"
            f"🎯 Taux de conversion : {stats.get('conversion', '0%')}\n\n"
            f"🏆 Produit top : {stats.get('top_product', '-')}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📤 Exporter CSV", callback_data="export_csv"),
                InlineKeyboardButton("🔙 Retour", callback_data="go_back")
            ]
        ])

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    @staticmethod
    async def export_csv(update: Update, context: CallbackContext) -> None:
        """Gère l'export des statistiques en CSV"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            await query.edit_message_text("❌ Permission refusée")
            return

        try:
            csv_data = db.export_stats_to_csv(user_id)
            await context.bot.send_document(
                chat_id=user_id,
                document=csv_data,
                filename="statistiques.csv",
                caption="📊 Export CSV des statistiques"
            )
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            await query.edit_message_text("❌ Erreur lors de l'export")

def setup_admin_handlers(application):
    """Configure les handlers administrateur"""
    application.add_handler(CommandHandler("stats", AdminStatsManager.handle_stats))
    application.add_handler(
        CallbackQueryHandler(
            AdminStatsManager.export_csv,
            pattern="^export_csv$"
        )
    )