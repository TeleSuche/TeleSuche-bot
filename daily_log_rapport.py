from datetime import datetime
telegram_gemini_5/schedulers/daily_log_report.py

from datetime import datetime, timedelta
from telegram.ext import Application from utils.memory_full import db

async def send_daily_log_report(context): pdg = db.get("pdg_bot") if not pdg or "owner" not in pdg: return

logs = db.get("log_archive", [])
recent = [
    log for log in logs
    if datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") >= datetime.now() - timedelta(days=1)
]

bot_count = sum(1 for l in recent if l["type"] == "BOT")
group_count = sum(1 for l in recent if l["type"] == "GROUPE")
canal_count = sum(1 for l in recent if l["type"] == "CANAL")

user_activity = {}
for log in recent:
    uid = log["user_id"]
    user_activity[uid] = user_activity.get(uid, 0) + 1

top_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:3]

text = (
    "📊 <b>Rapport journalier des logs</b>\n\n"
    f"🕓 Date : {datetime.now().strftime('%Y-%m-%d')}\n"
    f"• BOT: {bot_count}\n"
    f"• GROUPE: {group_count}\n"
    f"• CANAL: {canal_count}\n\n"
)

if top_users:
    text += "🏅 <b>Utilisateurs les plus actifs</b>\n"
    for uid, count in top_users:
        text += f"👤 <code>{uid}</code> — {count} logs\n"

await context.bot.send_message(pdg["owner"], text, parse_mode="HTML")
if pdg.get("log_channel"):
    await context.bot.send_message(pdg["log_channel"], text, parse_mode="HTML")

--- SETUP ---

def setup_daily_report(application: Application): from apscheduler.triggers.cron import CronTrigger application.job_queue.run_daily( send_daily_log_report, time=datetime.strptime("08:00", "%H:%M").time(), name="daily_log_report" )