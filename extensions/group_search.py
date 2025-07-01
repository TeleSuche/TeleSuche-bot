import logging
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from utils.memory_full import db

logger = logging.getLogger(__name__)

def register_group_search(dispatcher):
    def set_search_group(update: Update, context: CallbackContext):
        try:
            # Vérifier les droits admin
            if not db.is_group_admin(update.message.from_user.id, update.message.chat.id):
                update.message.reply_text("❌ Droits administrateur requis")
                return
                
            # Enregistrer le groupe
            db.set_search_group(update.message.from_user.id, update.message.chat.id)
            update.message.reply_text(
                f"✅ Groupe configuré pour la recherche!\n"
                f"Les fichiers seront maintenant indexés pour les recherches."
            )
        except Exception as e:
            logger.error(f"Erreur addgroupsearch: {e}")

    def set_reward_rules(update: Update, context: CallbackContext):
        try:
            # Vérifier les droits admin
            if not db.is_group_admin(update.message.from_user.id, update.message.chat.id):
                update.message.reply_text("❌ Droits administrateur requis")
                return
                
            # Vérifier les arguments
            if len(context.args) != 2:
                update.message.reply_text(
                    "Usage: /rewardrules <type> <montant>\nTypes: document, video, photo, audio"
                )
                return
                
            file_type = context.args[0]
            amount = int(context.args[1])
            
            # Mettre à jour les règles
            db.set_reward_rule(update.message.chat.id, file_type, amount)
            update.message.reply_text(f"✅ Récompense pour {file_type} fixée à {amount} crédits")
            
        except Exception as e:
            logger.error(f"Erreur rewardrules: {e}")

    def list_environments(update: Update, context: CallbackContext):
        try:
            groups = db.get_user_groups(update.message.from_user.id)
            if not groups:
                update.message.reply_text("❌ Aucun groupe enregistré")
                return
                
            response = "📋 Groupes où je suis actif:\n\n"
            for group in groups:
                response += f"• {group['title']} (ID: {group['id']})\n"
                
            update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Erreur environnements: {e}")

    # Enregistrement des handlers
    dispatcher.add_handler(CommandHandler("addgroupsearch", set_search_group))
    dispatcher.add_handler(CommandHandler("rewardrules", set_reward_rules))
    dispatcher.add_handler(CommandHandler("environnements", list_environments))