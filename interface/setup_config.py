import logging
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters
from typing import Dict

class BotConfigHandler:
    """Gestionnaire de configuration du bot avec suivi d'état"""

    def __init__(self):
        self.user_states: Dict[int, str] = {}  # {user_id: state}

    async def handle_setup_request(self, update: Update, context: CallbackContext) -> None:
        """Démarre le processus de configuration"""
        query = update.callback_query
        await query.answer()

        try:
            await query.delete_message()
        except Exception as e:
            logger.debug(f"Could not delete message: {e}")

        user_id = update.effective_user.id
        self.user_states[user_id] = "awaiting_bot_name"
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⚙️ Envoyez le nouveau nom ou description de votre bot.",
            parse_mode="HTML"
        )

    async def handle_bot_config_input(self, update: Update, context: CallbackContext) -> None:
        """Traite les entrées de configuration"""
        user_id = update.effective_user.id
        current_state = self.user_states.get(user_id)

        if not current_state:
            return

        text = update.message.text

        if current_state == "awaiting_bot_name":
            # Sauvegarder le nom et demander la description
            context.user_data['new_bot_name'] = text
            self.user_states[user_id] = "awaiting_bot_description"
            
            await update.message.reply_text(
                "📝 Maintenant, envoyez la nouvelle description pour votre bot:",
                parse_mode="HTML"
            )
        elif current_state == "awaiting_bot_description":
            # Finaliser la configuration
            context.user_data['new_bot_description'] = text
            del self.user_states[user_id]
            
            await update.message.reply_text(
                "✅ Configuration de base mise à jour avec succès!\n\n"
                f"Nom: {context.user_data['new_bot_name']}\n"
                f"Description: {text}",
                parse_mode="HTML"
            )

    def setup_handlers(self, application):
        """Configure les handlers pour ce gestionnaire"""
        application.add_handler(
            CallbackQueryHandler(
                self.handle_setup_request, 
                pattern="^setup_basics$"
            )
        )
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_bot_config_input
            )
        )

# Utilisation
config_handler = BotConfigHandler()
config_handler.setup_handlers(application)