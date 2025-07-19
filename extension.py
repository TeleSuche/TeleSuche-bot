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
from interface.stats import setup_admin_handlers # MODIFIÉ ICI
import logging

logger = logging.getLogger(__name__)

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

def register_bot_fils_extensions(application):
    """Enregistre toutes les extensions du bot fils"""
    register_search_handler(application)
    register_addstore(application)
    register_store_manager(application)
    register_store_checkout(application)
    register_createdon(application)
    register_user_history(application)
    setup_admin_handlers(application) # MODIFIÉ ICI

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