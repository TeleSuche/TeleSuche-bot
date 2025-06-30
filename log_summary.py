from datetime import datetime
telegram_gemini_5/handlers/log_summary.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext from utils.memory_full import db from datetime import datetime, timedelta

MAX_LOGS_PER_PAGE = 10 LOG_TYPES = ["ALL", "BOT", "GROUPE", "CANAL"]

def build_log_keyboard(page, total, active_type): nav = [] if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=f"log:{active_type}:{page-1}")) if page < total: nav.append(InlineKeyboardButton("➡️", callback_data=f"log:{active_type}:{page+1}"))

filters = [
    InlineKeyboardButton(t, callback_data=f"log:{t}:1") for t in LOG_TYPES if t != active_type
]
return InlineKeyboardMarkup([nav] if nav else [] + [filters] if filters else [])

async def pdg_log_summary(update: Update, context: CallbackContext): user_id = update.effective_user.id pdg = db.get("pdg_bot") if not pdg or pdg.get("owner") != user_id: return await update.message.reply_text("⛔️ Accès refusé. Commande réservée au PDG.")

logs = db.get("log_archive", [])
recent = [
    log for log in logs
    if datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") >= datetime.now() - timedelta(hours=24)
]

page = int(context.args[1]) if len(context.args) > 1 else 1
log_type = context.args[0].upper() if context.args else "ALL"

if log_type != "ALL":
    recent = [l for l in recent if l["type"] == log_type]

total_pages = (len(recent) + MAX_LOGS_PER_PAGE - 1) // MAX_LOGS_PER_PAGE
start = (page - 1) * MAX_LOGS_PER_PAGE
end = start + MAX_LOGS_PER_PAGE

if not recent:
    return await update.message.reply_text("✅ Aucun log trouvé pour les dernières 24 heures.")

bot_count = sum(1 for l in recent if l["type"] == "BOT")

group_count = sum(1 for l in recent if l["type"] == "GROUPE") canal_count = sum(1 for l in recent if l["type"] == "CANAL") text = f"🗂 <b>Logs {log_type} (24h)</b> — Page {page}/{total_pages} 👁️ BOT: {bot_count} | GROUPE: {group_count} | CANAL: {canal_count}

" for entry in recent[start:end]: text += f"<b>{entry['type']}</b> — {entry['timestamp']}\n👤 {entry['user_id']} ({entry['plan']})\n\n"

await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_log_keyboard(page, total_pages, log_type))

async def handle_log_pagination(update: Update, context: CallbackContext): query = update.callback_query await query.answer()

_, log_type, page = query.data.split(":")
page = int(page)

logs = db.get("log_archive", [])
recent = [
    log for log in logs
    if datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") >= datetime.now() - timedelta(hours=24)
]
if log_type != "ALL":
    recent = [l for l in recent if l["type"] == log_type]

total_pages = (len(recent) + MAX_LOGS_PER_PAGE - 1) // MAX_LOGS_PER_PAGE
start = (page - 1) * MAX_LOGS_PER_PAGE
end = start + MAX_LOGS_PER_PAGE

bot_count = sum(1 for l in recent if l["type"] == "BOT")

group_count = sum(1 for l in recent if l["type"] == "GROUPE") canal_count = sum(1 for l in recent if l["type"] == "CANAL") text = f"🗂 <b>Logs {log_type} (24h)</b> — Page {page}/{total_pages} 👁️ BOT: {bot_count} | GROUPE: {group_count} | CANAL: {canal_count}

" for entry in recent[start:end]: text += f"<b>{entry['type']}</b> — {entry['timestamp']}\n👤 {entry['user_id']} ({entry['plan']})\n\n"

await query.edit_message_text(text, parse_mode="HTML", reply_markup=build_log_keyboard(page, total_pages, log_type))

--- SETUP ---

def setup(application: Application): application.add_handler(CommandHandler("logsummary", pdg_log_summary)) application.add_handler(CallbackQueryHandler(handle_log_pagination, pattern=r"^log:.+:\d+$"))