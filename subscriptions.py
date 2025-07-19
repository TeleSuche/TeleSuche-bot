# subscriptions.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from datetime import datetime, timedelta
from utils.memory_full import db

PLANS = {
    "sub_basic": {
        "label": "🌸 Essentiel",
        "features": ["1 bot", "2 groupes", "1 canal", "commandes basiques"],
        "limits": {"bots": 1, "groups": 2, "channels": 1},
    },
    "sub_avance": {
        "label": "🔅 Avancé",
        "features": ["2 bots", "5 groupes", "2 canaux", "commandes avancées"],
        "limits": {"bots": 2, "groups": 5, "channels": 2},
    },
    "sub_premium": {
        "label": "✴️ Premium",
        "features": ["3 bots", "10 groupes", "3 canaux", "fonctionnalités premium"],
        "limits": {"bots": 3, "groups": 10, "channels": 3},
    },
    "sub_pro": {
        "label": "💼 Pro",
        "features": ["5 bots", "20 groupes", "5 canaux", "statistiques, logs, UI avancée"],
        "limits": {"bots": 5, "groups": 20, "channels": 5},
    },
    "sub_ultime": {
        "label": "🚀 Ultime",
        "features": ["bots illimités", "groupes illimités", "toutes les commandes IA, UI, logs"],
        "limits": {"bots": 999, "groups": 999, "channels": 999},
    },
}


def get_user_plan(user_id: int) -> str:
    return db.get("user_plans", {}).get(user_id, "sub_basic")


def get_plan_limits(plan: str) -> dict:
    return PLANS.get(plan, {}).get(
        "limits", {"bots": 1, "groups": 2, "channels": 1}
    )


async def show_user_plan(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_id = update.effective_user.id
    plan = get_user_plan(user_id)
    data = PLANS.get(plan, {})
    label = data.get("label", plan)
    features = data.get("features", [])

    text = (
        "🧾 <b>Votre abonnement</b>\n"
        f"Plan actuel: <b>{label}</b>\n\n"
        "Fonctionnalités :\n"
    )
    for feat in features:
        text += f"• {feat}\n"

    keyboard = [
        [
            InlineKeyboardButton(
                "🆙 Passer à un plan supérieur", callback_data="upgrade_plan"
            )
        ]
    ]
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def handle_upgrade_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les options de mise à niveau"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = "fr"  # À adapter selon votre système de langue
    
    text = (
        "🆙 <b>Mise à niveau de votre abonnement</b>\n\n"
        "Sélectionnez un plan pour voir les détails :"
    )
    
    keyboard = []
    for plan_id, plan_data in PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                plan_data["label"],
                callback_data=f"plan_details:{plan_id}"
            )
        ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def show_plan_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les détails d'un plan spécifique"""
    query = update.callback_query
    await query.answer()
    plan_id = query.data.split(":")[1]
    plan_data = PLANS.get(plan_id, {})
    
    text = (
        f"📊 <b>{plan_data.get('label', 'Détails du plan')}</b>\n\n"
        "Fonctionnalités incluses :\n"
    )
    for feature in plan_data.get("features", []):
        text += f"• {feature}\n"
    
    text += "\n💳 Prix : À compléter\n\n"  # Ajoutez vos prix ici
    
    keyboard = [
        [InlineKeyboardButton("💳 Souscrire", callback_data=f"subscribe:{plan_id}")],
        [InlineKeyboardButton("🔙 Retour", callback_data="upgrade_plan")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def check_bot_limits(user_id: int) -> bool:
    plan = get_user_plan(user_id)
    limits = get_plan_limits(plan)
    bots = db.get_user_bots(user_id)
    
    # Filtrer les bots actifs (non supprimés)
    active_bots = [b for b in bots if not b.get('deletion_scheduled')]
    current_count = len(active_bots)
    
    # Vérifier la période de 14 jours
    now = datetime.now()
    for bot in active_bots:
        created_at = datetime.fromisoformat(bot['creation_time'])
        if (now - created_at).days > 14:
            # Après 14 jours, appliquer les limites du plan
            return current_count < limits["bots"]
    
    # Pendant les 14 premiers jours, autoriser jusqu'à 10 bots
    return current_count < 10


async def check_group_limits(user_id: int, new_group_id: int) -> bool:
    plan = get_user_plan(user_id)
    limits = get_plan_limits(plan)
    bots = db.get_user_bots(user_id)
    total_groups = sum(len(bot.get("groups", [])) for bot in bots)
    return total_groups < limits["groups"]


def setup(application: Application) -> None:
    application.add_handler(
        CommandHandler("monabonnement", show_user_plan)
    )
    application.add_handler(CallbackQueryHandler(handle_upgrade_plan, pattern="^upgrade_plan$"))
    application.add_handler(CallbackQueryHandler(show_plan_details, pattern=r"^plan_details:"))