import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from uuid import uuid4
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Stockage des liens (pourrait être remplacé par une base de données)
link_storage: Dict[str, Dict] = {}

class PaymentLinkManager:
    """Gestionnaire des liens de paiement avec suivi analytique"""

    @staticmethod
    def generate_payment_link(user_id: int, product: Dict[str, Any]) -> str:
        """Génère un lien de paiement unique avec token"""
        token = str(uuid4())[:8]
        link = f"https://pay.telesuche.ai/{user_id}/{token}"
        
        link_storage[link] = {
            "user_id": user_id,
            "data": product,
            "clicks": 0,
            "active": True,
            "created_at": datetime.now()
        }
        logger.info(f"New payment link generated for user {user_id}")
        return link

    @staticmethod
    async def handle_generate_link(update: Update, context: CallbackContext):
        """Génère un nouveau lien de paiement"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        
        # Récupération des données temporaires (à adapter selon votre implémentation)
        data = context.chat_data.get('temp_payment_data')
        if not data:
            await query.edit_message_text("❌ Données manquantes. Veuillez recommencer.")
            return

        link = PaymentLinkManager.generate_payment_link(user_id, data)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🔗 Lien de paiement généré :\n"
                f"<code>{link}</code>\n\n"
                "⚙️ Utilisez ce lien dans vos publications.\n"
                "Vous pouvez modifier le contenu à tout moment."
            ),
            parse_mode="HTML"
        )

    @staticmethod
    async def handle_show_info(update: Update, context: CallbackContext):
        """Affiche les statistiques des liens"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        entries = [k for k, v in link_storage.items() if v['user_id'] == user_id]
        
        if not entries:
            await query.edit_message_text("📭 Aucun lien actif trouvé.")
            return

        text = "📊 Statistiques de vos liens :\n\n"
        for link in entries[:5]:  # Limite à 5 liens pour éviter les messages trop longs
            data = link_storage[link]
            text += (
                f"• Lien : <code>{link}</code>\n"
                f"  👆 {data['clicks']} clics | "
                f"🔄 {data['active'] and 'Actif' or 'Inactif'}\n"
                f"  🕒 Créé le : {data['created_at'].strftime('%d/%m/%Y')}\n\n"
            )
        
        if len(entries) > 5:
            text += f"\nℹ️ {len(entries) - 5} autres liens non affichés"

        await query.edit_message_text(
            text=text,
            parse_mode="HTML"
        )

    @staticmethod
    async def handle_edit_link(update: Update, context: CallbackContext):
        """Gère la modification des liens"""
        query = update.callback_query
        await query.answer("🛠️ Fonction de modification à venir. Veuillez recréer le lien.")

def setup_payment_handlers(application):
    """Configure les handlers pour la gestion des paiements"""
    application.add_handler(
        CallbackQueryHandler(
            PaymentLinkManager.handle_generate_link,
            pattern="^generate_link$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            PaymentLinkManager.handle_show_info,
            pattern="^info_link$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            PaymentLinkManager.handle_edit_link,
            pattern="^edit_link$"
        )
    )