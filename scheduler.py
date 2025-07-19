from telegram.ext import ContextTypes, Application
from datetime import datetime
from utils.memory_full import db
from . import config  # import send_configured
import asyncio

# Format attendu :
# db["recurrent_timers"] = {
#   bot_id: [
#       {"chat_id": 1234, "config_key": "recurrent_annonce", "delay": 3600}
#   ]
# }

recurrent_timers = db.get("recurrent_timers", {})

async def scheduler_loop(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.utcnow()
    for bot_id, messages in recurrent_timers.items():
        for entry in messages:
            chat_id = entry["chat_id"]
            delay = entry["delay"]
            key = f"last:{bot_id}:{chat_id}:{entry.get('config_key', '')}"
            last = db.get(key, datetime.min)

            if (now - last).total_seconds() >= delay:
                await config.send_configured(context, chat_id, bot_id, entry["config_key"])
                db[key] = now

# --- SETUP ---
def setup(application: Application):
    application.job_queue.run_repeating(scheduler_loop, interval=60)
--------
Son entrée db créé via /config ( db["recurrent_timers"]["BOT_ID"] = [
    {
        "chat_id": -100123456789,
        "config_key": "recurrent_rappel",
        "delay": 3600  # toutes les heures
    }
]  )
