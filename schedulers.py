"""Planificateur pour les messages récurrents"""
import logging
from datetime import datetime
from telegram.ext import ContextTypes, Application
from utils.memory_full import db

logger = logging.getLogger(__name__)

async def scheduler_loop(context: ContextTypes.DEFAULT_TYPE):
    """Tâche récurrente pour l'envoi de messages programmés"""
    now = datetime.utcnow()
    recurrent_timers = db.get("recurrent_timers", {})
    
    for bot_id, messages in recurrent_timers.items():
        for entry in messages:
            chat_id = entry["chat_id"]
            delay = entry["delay"]
            key = f"last:{bot_id}:{chat_id}:{entry.get('config_key', '')}"
            last = db.get(key, datetime.min)

            if (now - last).total_seconds() >= delay:
                # Fonction hypothétique - à implémenter
                # await send_configured_message(context, chat_id, bot_id, entry["config_key"])
                db.set(key, now)
                logger.info(f"Message envoyé à {chat_id} via bot {bot_id}")

def setup(application: Application):
    """Configuration du planificateur"""
    application.job_queue.run_repeating(scheduler_loop, interval=60)