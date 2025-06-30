import logging
logger = logging.getLogger(__name__)
# pdg_bot.py
import logging
import threading
from telegram.ext import Application
from utils.memory_full import db
from handlers.pdg_dashboard import setup as setup_pdg_dashboard
from handlers.log_summary import setup as setup_log_summary
from handlers.pdg_alerts import schedule_pdg_alerts
from schedulers.daily_log_report import setup_daily_report

logger = logging.getLogger(__name__)

def init_pdg_bot():
    """Initialise et démarre le bot PDG si configuré"""
    pdg_config = db.get("pdg_bot")
    if not pdg_config or "token" not in pdg_config:
        logger.warning("Aucun token configuré pour le bot PDG.")
        return
    
    token = pdg_config["token"]
    try:
        application = Application.builder().token(token).build()
        
        # Enregistrement des handlers spécifiques au PDG
        setup_pdg_dashboard(application)
        setup_log_summary(application)
        
        # Planification des tâches PDG
        schedule_pdg_alerts(application)
        setup_daily_report(application)
        
        # Démarrer le bot dans un thread séparé
        thread = threading.Thread(target=application.run_polling, daemon=True)
        thread.start()
        logger.info(f"Bot PDG démarré avec le token: {token[:6]}...")
    except Exception as e:
        logger.error(f"Erreur démarrage bot PDG: {e}")