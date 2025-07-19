from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext.callbackcontext import CallbackContext
import subprocess
import time
import os
from utils.memory_full import db
from datetime import datetime
from extensions.handlers.search_handler import register_search_handler
from interface.addstore import register_addstore
from interface.store_manager import register_store_manager
from interface.store_checkout import register_store_checkout
from interface.createdon import register_createdon
from interface.history import register_user_history
from interface.stats import register_admin_stats

def log(message, level="INFO"):
    """Affiche un message coloré avec horodatage"""
    now = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": "\033[94m",     # Bleu
        "SUCCESS": "\033[92m",  # Vert
        "WARNING": "\033[93m",  # Jaune
        "ERROR": "\033[91m",    # Rouge
        "RESET": "\033[0m"      # Reset
    }
    print(f"{colors.get(level, '')}[{now}] {message}{colors['RESET']}")

def register_bot_fils_extensions(dispatcher):
    """Enregistre toutes les extensions du bot fils avec PTB"""
    register_search_handler(dispatcher)
    register_addstore(dispatcher)
    register_store_manager(dispatcher)
    register_store_checkout(dispatcher)
    register_createdon(dispatcher)
    register_user_history(dispatcher)
    register_admin_stats(dispatcher)

def register_group_manager(dispatcher):
    """Gestion des groupes pour les administrateurs avec PTB"""
    
    def set_main_group(update: Update, context: CallbackContext):
        if not db.is_admin(update.message.from_user.id):
            return
            
        db.set_main_group(update.message.from_user.id, update.message.chat.id)
        update.message.reply_text(
            f"✅ Groupe principal défini:\n"
            f"Nom: {update.message.chat.title}\n"
            f"ID: {update.message.chat.id}"
        )

    def set_group_rules(update: Update, context: CallbackContext):
        if not context.args:
            update.message.reply_text("Usage: /grouprules <texte>")
            return
            
        rules_text = ' '.join(context.args)
        db.set_group_rules(update.message.chat.id, rules_text)
        update.message.reply_text("✅ Règles du groupe mises à jour")

    dispatcher.add_handler(CommandHandler("setgroup", set_main_group))
    dispatcher.add_handler(CommandHandler("grouprules", set_group_rules))

def start_all_fils_bots():
    tokens = db.get_all_admin_bot_tokens()

    if not tokens:
        log("❌ Aucun token trouvé dans la base de données.", "ERROR")
        return

    script_path = os.path.join(os.path.dirname(__file__), "run_fils_bot.py")

    log(f"🔄 {len(tokens)} bots vont être lancés...\n", "INFO")

    for token in tokens:
        short_token = token[:10] + "..."
        log(f"🚀 Lancement du bot (token: {short_token})...", "INFO")

        try:
            subprocess.Popen(["python3", script_path, token])
            log("✅ Bot démarré en arrière-plan.", "SUCCESS")
        except Exception as e:
            log(f"❌ Erreur lancement bot {short_token} : {e}", "ERROR")

        time.sleep(1)  # Pause entre les bots

    log("\n✅ Tous les bots ont été lancés !", "SUCCESS")

if __name__ == "__main__":
    start_all_fils_bots()