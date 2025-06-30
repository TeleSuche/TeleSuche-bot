telegram_gemini_5/handlers/pdg_alerts.py

from telegram.ext import CallbackContext from datetime import datetime
from utils.memory_full import db

PDG_ID = 123456789  # À personnaliser

async def check_alerts(context: CallbackContext): bot = context.bot alerts = []

# Vérifier les bots inactifs
inactive_bots = db.get_inactive_bots()
for bot_info in inactive_bots:
    alerts.append(f"🔴 Bot inactif : @{bot_info['username']} depuis {bot_info['last_active']}")

# Vérifier les abonnements expirés
expired = db.get_expired_subscriptions()
for sub in expired:
    alerts.append(f"⌛ Abonnement expiré : {sub['bot_username']} (Plan {sub['plan']})")

# Vérifier crédits des admins
low = db.get_low_credit_admins()
for adm in low:
    alerts.append(f"⚠️ Admin @{adm['username']} n’a plus de crédits.")

# Envoi s’il y a des alertes
if alerts:
    text = "📣 <b>Alertes système</b>\n\n" + "\n".join(alerts)
    try:
        await bot.send_message(PDG_ID, text, parse_mode="HTML")
    except:
        pass

--- Intégration JobQueue ---

def schedule_pdg_alerts(application): application.job_queue.run_repeating(check_alerts, interval=1800, first=10)