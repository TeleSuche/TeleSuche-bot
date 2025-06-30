telegram_gemini_5/handlers/pdg_dashboard.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler from utils.memory_full import db

--- COMMANDES ---

async def show_pdg_dashboard(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass stats = db.get_system_overview() text = ( "📊 <b>Tableau de bord - PDG</b>\n\n" f"👥 Bots créés : <b>{stats['bots_total']}</b>\n" f"🟢 Actifs : <b>{stats['bots_active']}</b>\n" f"🔴 Inactifs : <b>{stats['bots_inactive']}</b>\n" f"👤 Admins : <b>{stats['admins_total']}</b>\n" f"📌 Groupes utilisés : <b>{stats['groups_total']}</b>\n" f"📎 Abonnements : <b>{stats['subscriptions_total']}</b>\n" ) keyboard = [ [InlineKeyboardButton("📜 Liste bots", callback_data="pdg_bots_list"), InlineKeyboardButton("👤 Admins", callback_data="pdg_admins_list")], [InlineKeyboardButton("🧾 Abonnements", callback_data="pdg_subscriptions")], [InlineKeyboardButton("📋 Logs activité", callback_data="pdg_logs")] ] await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

--- CALLBACKS ---

async def handle_pdg_callback(update: Update, context: CallbackContext): query = update.callback_query data = query.data try: await query.message.delete() except: pass

if data == "pdg_bots_list":
    bots = db.get_all_bots()
    msg = "🤖 <b>Bots enfants :</b>\n" + "\n".join([f"• @{b['username']} ({b['status']})" for b in bots])
elif data == "pdg_admins_list":
    admins = db.get_all_admins()
    msg = "👤 <b>Administrateurs :</b>\n" + "\n".join([f"• {a['name']} ({a['id']})" for a in admins])
elif data == "pdg_subscriptions":
    subs = db.get_all_subscriptions()
    msg = "🧾 <b>Abonnements :</b>\n" + "\n".join([f"• {s['bot']} → {s['plan']}" for s in subs])
elif data == "pdg_logs":
    logs = db.get_recent_logs()
    msg = "📋 <b>Activité récente :</b>\n" + "\n".join(logs[:15])
else:
    msg = "❌ Action inconnue"

await query.message.reply_text(msg, parse_mode="HTML")

--- INTÉGRATION ---

def setup(application): application.add_handler(CommandHandler("start", show_pdg_dashboard)) application.add_handler(CommandHandler("pdgmenu", show_pdg_dashboard)) application.add_handler(CallbackQueryHandler(handle_pdg_callback, pattern="^pdg_"))
