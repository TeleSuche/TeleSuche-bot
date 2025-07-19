"""Génération des rapports journaliers de logs"""
import logging
from datetime import datetime, timedelta
from telegram.ext import Application, CallbackContext
from utils.memory_full import db

logger = logging.getLogger(__name__)

async def send_daily_log_report(context: CallbackContext):
    """Envoie le rapport journalier des logs"""
    pdg_config = db.get("pdg_bot", {})
    if not pdg_config or "owner" not in pdg_config:
        return

    logs = db.get("log_archive", [])
    recent = [
        log for log in logs
        if datetime.now() - datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") <= timedelta(days=1)
    ]

    counts = {
        "BOT": 0,
        "GROUPE": 0,
        "CANAL": 0
    }
    user_activity = {}
    
    for log in recent:
        log_type = log.get("type", "INCONNU")
        if log_type in counts:
            counts[log_type] += 1
        
        uid = log.get("user_id", "INCONNU")
        user_activity[uid] = user_activity.get(uid, 0) + 1

    top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:3]

    text = (
        "📊 <b>Rapport journalier des logs</b>\n\n"
        f"🕓 Période : {datetime.now().strftime('%Y-%m-%d')}\n"
        f"• BOT: {counts['BOT']}\n"
        f"• GROUPE: {counts['GROUPE']}\n"
        f"• CANAL: {counts['CANAL']}\n\n"
    )

    if top_users:
        text += "🏅 <b>Top utilisateurs</b>\n"
        for uid, count in top_users:
            text += f"👤 <code>{uid}</code> — {count} actions\n"

    try:
        await context.bot.send_message(pdg_config["owner"], text, parse_mode="HTML")
        if "log_channel" in pdg_config:
            await context.bot.send_message(pdg_config["log_channel"], text, parse_mode="HTML")
    except Exception as e:
        logger.error("Erreur envoi rapport: %s", e)

def setup_daily_report(application: Application):
    """Planifie le rapport journalier"""
    application.job_queue.run_daily(
        send_daily_log_report,
        time=datetime.strptime("08:00", "%H:%M").time(),
        days=tuple(range(7)),  # Tous les jours de 0 (lundi) à 6 (dimanche)
        name="daily_log_report"
    )