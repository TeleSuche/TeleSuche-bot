"""Gestion des alertes système pour le PDG"""
import logging
from telegram.ext import CallbackContext
from utils.memory_full import db

logger = logging.getLogger(__name__)
PDG_ID = 1001157044  # À remplacer par votre ID

async def check_alerts(context: CallbackContext):
    """Vérifie et envoie les alertes système"""
    bot = context.bot
    alerts = []

    # Vérifier les bots inactifs
    inactive_bots = db.get("inactive_bots", [])
    for bot_info in inactive_bots:
        alerts.append(f"🔴 Bot inactif : @{bot_info.get('username', 'inconnu')} depuis {bot_info.get('last_active', 'N/A')}")

    # Vérifier les abonnements expirés
    expired_subs = db.get("expired_subscriptions", [])
    for sub in expired_subs:
        alerts.append(f"⌛ Abonnement expiré : {sub.get('bot_username', 'inconnu')} (Plan {sub.get('plan', 'N/A')})")

    # Vérifier crédits des admins
    low_credit_admins = db.get("low_credit_admins", [])
    for adm in low_credit_admins:
        alerts.append(f"⚠️ Admin @{adm.get('username', 'inconnu')} n'a plus de crédits")

    # Envoi s'il y a des alertes
    if alerts:
        text = "📣 <b>Alertes système</b>\n\n" + "\n".join(alerts)
        try:
            await bot.send_message(PDG_ID, text, parse_mode="HTML")
        except Exception as e:
            logger.error("Erreur envoi alertes: %s", e)

def schedule_pdg_alerts(application):
    """Planifie les vérifications d'alertes"""
    if application.job_queue:
        application.job_queue.run_repeating(check_alerts, interval=1800, first=10)
    else:
        logger.warning("JobQueue non disponible pour les alertes PDG")