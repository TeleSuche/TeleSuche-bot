"""Gestion des résumés de logs pour le PDG"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from utils.memory_full import db

logger = logging.getLogger(__name__)
MAX_LOGS_PER_PAGE = 10
LOG_TYPES = ["ALL", "BOT", "GROUPE", "CANAL"]

def build_log_keyboard(page, total_pages, active_type):
    """Construit le clavier de pagination et de filtrage"""
    keyboard = []
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"log:{active_type}:{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="log:noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"log:{active_type}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    type_buttons = []
    for log_type in LOG_TYPES:
        if log_type == active_type:
            type_buttons.append(InlineKeyboardButton(f"✅ {log_type}", callback_data=f"log:{log_type}:1"))
        else:
            type_buttons.append(InlineKeyboardButton(log_type, callback_data=f"log:{log_type}:1"))
    
    if type_buttons:
        keyboard.append(type_buttons)
        
    return InlineKeyboardMarkup(keyboard)

async def pdg_log_summary(update: Update, context: CallbackContext):
    """Affiche le résumé des logs pour le PDG"""
    user_id = update.effective_user.id
    pdg_config = db.get("pdg_bot", {})
    
    if not pdg_config or pdg_config.get("owner") != user_id:
        return await update.message.reply_text("⛔️ Accès refusé. Commande réservée au PDG.")
    
    args = context.args
    log_type = args[0].upper() if args and args[0].upper() in LOG_TYPES else "ALL"
    try:
        page = int(args[1]) if len(args) > 1 else 1
    except:
        page = 1

    logs = db.get("log_archive", [])
    recent = [
        log for log in logs
        if datetime.now() - datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") <= timedelta(days=1)
    ]
    
    if log_type != "ALL":
        recent = [log for log in recent if log["type"] == log_type]
    
    total_pages = max(1, (len(recent) + MAX_LOGS_PER_PAGE - 1) // MAX_LOGS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * MAX_LOGS_PER_PAGE
    end_idx = start_idx + MAX_LOGS_PER_PAGE
    page_logs = recent[start_idx:end_idx]
    
    if not recent:
        return await update.message.reply_text("✅ Aucun log trouvé pour les dernières 24 heures.")
    
    counts = {t: sum(1 for log in recent if log["type"] == t) for t in LOG_TYPES[1:]}
    text = (
        f"🗂 <b>Logs {log_type} (24h)</b> — Page {page}/{total_pages}\n"
        f"👁️ BOT: {counts.get('BOT', 0)} | GROUPE: {counts.get('GROUPE', 0)} | CANAL: {counts.get('CANAL', 0)}\n\n"
    )
    
    for entry in page_logs:
        text += (
            f"<b>{entry.get('type', 'INCONNU')}</b> — {entry.get('timestamp', 'N/A')}\n"
            f"👤 {entry.get('user_id', 'N/A')} ({entry.get('plan', 'Aucun')})\n\n"
        )
    
    await update.message.reply_text(
        text, 
        parse_mode="HTML", 
        reply_markup=build_log_keyboard(page, total_pages, log_type)
    )

async def handle_log_pagination(update: Update, context: CallbackContext):
    """Gère la pagination des logs"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "log:noop":
        return
    
    parts = data.split(":")
    log_type = parts[1]
    page = int(parts[2])
    
    logs = db.get("log_archive", [])
    recent = [
        log for log in logs
        if datetime.now() - datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S") <= timedelta(days=1)
    ]
    
    if log_type != "ALL":
        recent = [log for log in recent if log["type"] == log_type]
    
    total_pages = max(1, (len(recent) + MAX_LOGS_PER_PAGE - 1) // MAX_LOGS_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * MAX_LOGS_PER_PAGE
    end_idx = start_idx + MAX_LOGS_PER_PAGE
    page_logs = recent[start_idx:end_idx]
    
    counts = {t: sum(1 for log in recent if log["type"] == t) for t in LOG_TYPES[1:]}
    text = (
        f"🗂 <b>Logs {log_type} (24h)</b> — Page {page}/{total_pages}\n"
        f"👁️ BOT: {counts.get('BOT', 0)} | GROUPE: {counts.get('GROUPE', 0)} | CANAL: {counts.get('CANAL', 0)}\n\n"
    )
    
    for entry in page_logs:
        text += (
            f"<b>{entry.get('type', 'INCONNU')}</b> — {entry.get('timestamp', 'N/A')}\n"
            f"👤 {entry.get('user_id', 'N/A')} ({entry.get('plan', 'Aucun')})\n\n"
        )
    
    await query.edit_message_text(
        text, 
        parse_mode="HTML", 
        reply_markup=build_log_keyboard(page, total_pages, log_type)
    )

def setup(application):
    """Configure les handlers pour les logs"""
    application.add_handler(CommandHandler("logsummary", pdg_log_summary))
    application.add_handler(CallbackQueryHandler(handle_log_pagination, pattern=r"^log:"))