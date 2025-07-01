import subprocess
import time
import os
from utils.memory_full import db
from datetime import datetime

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