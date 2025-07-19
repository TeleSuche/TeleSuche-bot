import subprocess
import time
import os
import sys
import logging
from utils.memory_full import db
from datetime import datetime

# Configuration du logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start_all_fils_bots():
    tokens = db.get_all_admin_bot_tokens()

    if not tokens:
        logger.error("❌ Aucun token trouvé dans la base de données.")
        return

    # Chemin absolu vers le script à exécuter
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "run_fils_bot.py")
    
    if not os.path.exists(script_path):
        logger.error(f"❌ Fichier run_fils_bot.py introuvable à l'emplacement: {script_path}")
        return

    logger.info(f"🔄 {len(tokens)} bots vont être lancés...")

    for token in tokens:
        short_token = token[:10] + "..."
        logger.info(f"🚀 Lancement du bot (token: {short_token})...")

        try:
            # Utilisation de sys.executable pour garantir le bon interpréteur Python
            subprocess.Popen([sys.executable, script_path, token])
            logger.info("✅ Bot démarré en arrière-plan.")
        except Exception as e:
            logger.error(f"❌ Erreur lancement bot {short_token} : {str(e)}")

        time.sleep(1)  # Pause entre les bots

    logger.info("✅ Tous les bots ont été lancés !")

if __name__ == "__main__":
    start_all_fils_bots()