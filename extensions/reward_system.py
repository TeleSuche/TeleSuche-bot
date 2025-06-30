import logging
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db
import logging

logger = logging.getLogger(__name__)

def register_reward_system(dispatcher):
    def accept_reward(update: Update, context: CallbackContext):
        query = update.callback_query
        try:
            # Extraire l'ID du message original
            original_msg_id = int(query.data.split("_")[-1])
            
            # Récupérer les données du fichier
            file_data = db.get_temp_file(original_msg_id)
            if not file_data:
                query.answer("❌ Fichier introuvable")
                return
                
            # Accorder la récompense
            reward = db.get_reward_for_type(file_data['type'])
            db.add_credits(query.from_user.id, file_data['group_id'], reward)
            
            # Sauvegarder le fichier
            db.save_file(file_data)
            
            # Confirmer à l'utilisateur
            query.edit_message_text(
                f"✅ Fichier enregistré! +{reward} crédits ajoutés à votre compte"
            )
            
        except Exception as e:
            logger.error(f"Erreur acceptation récompense: {e}")
            query.answer("❌ Erreur lors du traitement")

    def decline_reward(update: Update, context: CallbackContext):
        query = update.callback_query
        try:
            context.bot.delete_message(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id
            )
            query.answer("❌ Fichier non enregistré")
        except Exception as e:
            logger.error(f"Erreur refus récompense: {e}")

    # Enregistrement des handlers avec des patterns regex
    dispatcher.add_handler(CallbackQueryHandler(accept_reward, pattern=r"^accept_reward_\d+$"))
    dispatcher.add_handler(CallbackQueryHandler(decline_reward, pattern=r"^decline_reward_\d+$"))