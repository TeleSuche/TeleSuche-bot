"""Tableau de bord du PDG"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from utils.memory_full import db

logger = logging.getLogger(__name__)

async def show_pdg_dashboard(update: Update, context: CallbackContext):
    """Affiche le tableau de bord principal"""
    try:
        if update.callback_query:
            await update.callback_query.message.delete()
    except Exception as e:
        logger.error("Erreur suppression message: %s", e)
    
    stats = db.get("system_stats", {
        "bots_total": 0,
        "bots_active": 0,
        "bots_inactive": 0,
        "admins_total": 0,
        "groups_total": 0,
        "subscriptions_total": 0
    })
    
    text = (
        "📊 <b>Tableau de bord - PDG</b>\n\n"
        f"👥 Bots créés : <b>{stats['bots_total']}</b>\n"
        f"🟢 Actifs : <b>{stats['bots_active']}</b>\n"
        f"🔴 Inactifs : <b>{stats['bots_inactive']}</b>\n"
        f"👤 Admins : <b>{stats['admins_total']}</b>\n"
        f"📌 Groupes utilisés : <b>{stats['groups_total']}</b>\n"
        f"📎 Abonnements : <b>{stats['subscriptions_total']}</b>\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📜 Liste bots", callback_data="pdg_bots_list"), 
         InlineKeyboardButton("👤 Admins", callback_data="pdg_admins_list")],
        [InlineKeyboardButton("🧾 Abonnements", callback_data="pdg_subscriptions")],
        [InlineKeyboardButton("📋 Logs activité", callback_data="pdg_logs")]
    ]
    
    await update.effective_message.reply_text(
        text, 
        parse_mode="HTML", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_pdg_callback(update: Update, context: CallbackContext):
    """Gère les interactions du tableau de bord"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.message.delete()
    except Exception as e:
        logger.error("Erreur suppression message: %s", e)
    
    data = query.data
    if data == "pdg_bots_list":
        bots = db.get("all_bots", [])
        msg = "🤖 <b>Bots enfants :</b>\n" + "\n".join(
            [f"• @{b.get('username', 'inconnu')} ({b.get('status', 'N/A')})" for b in bots]
        )
    elif data == "pdg_admins_list":
        admins = db.get("all_admins", [])
        msg = "👤 <b>Administrateurs :</b>\n" + "\n".join(
            [f"• {a.get('name', 'inconnu')} ({a.get('id', 'N/A')})" for a in admins]
        )
    elif data == "pdg_subscriptions":
        subs = db.get("all_subscriptions", [])
        msg = "🧾 <b>Abonnements :</b>\n" + "\n".join(
            [f"• {s.get('bot', 'inconnu')} → {s.get('plan', 'N/A')}" for s in subs]
        )
    elif data == "pdg_logs":
        logs = db.get("recent_logs", [])
        msg = "📋 <b>Activité récente :</b>\n" + "\n".join(logs[:15])
    else:
        msg = "❌ Action inconnue"
    
    await query.message.reply_text(msg, parse_mode="HTML")

def setup(application):
    """Configure les handlers du tableau de bord"""
    application.add_handler(CommandHandler("start", show_pdg_dashboard))
    application.add_handler(CommandHandler("pdgmenu", show_pdg_dashboard))
    application.add_handler(CallbackQueryHandler(handle_pdg_callback, pattern="^pdg_"))