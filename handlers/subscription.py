from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext
from utils.memory_full import db

PLANS = {
    "sub_basic": {
        "label": "🌸 Essentiel",
        "features": ["1 bot", "2 groupes", "1 canal", "commandes basiques"],
        "limits": {"bots": 1, "groups": 2, "channels": 1}
    },
    "sub_avance": {
        "label": "🔅 Avancé", 
        "features": ["2 bots", "5 groupes", "2 canaux", "commandes avancées"],
        "limits": {"bots": 2, "groups": 5, "channels": 2}
    },
    "sub_premium": {
        "label": "✴️ Premium",
        "features": ["3 bots", "10 groupes", "3 canaux", "fonctionnalités premium"],
        "limits": {"bots": 3, "groups": 10, "channels": 3}
    },
    "sub_pro": {
        "label": "💼 Pro",
        "features": ["5 bots", "20 groupes", "5 canaux", "statistiques, logs, UI avancée"],
        "limits": {"bots": 5, "groups": 20, "channels": 5}
    },
    "sub_ultime": {
        "label": "🚀 Ultime",
        "features": ["bots illimités", "groupes illimités", "toutes les commandes IA, UI, logs"],
        "limits": {"bots": 999, "groups": 999, "channels": 999}
    }
}

class SubscriptionHandler:
    def __init__(self):
        pass

    def get_user_plan(self, user_id: int) -> str:
        return db.get("user_plans", {}).get(user_id, "sub_basic")

    def get_plan_limits(self, plan: str) -> dict:
        return PLANS.get(plan, {}).get("limits", {"bots": 1, "groups": 2, "channels": 1})

    async def show_user_plan(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        plan = self.get_user_plan(user_id)
        data = PLANS.get(plan, {})
        label = data.get("label", plan)
        features = data.get("features", [])

        text = f"🧾 <b>Votre abonnement</b>\nPlan actuel: <b>{label}</b>\n\nFonctionnalités :\n"
        for feat in features:
            text += f"• {feat}\n"

        keyboard = [
            [InlineKeyboardButton("🆙 Passer à un plan supérieur", callback_data="upgrade_plan")]
        ]
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="HTML"
        )

    async def check_bot_limits(self, user_id: int) -> bool:
        plan = self.get_user_plan(user_id)
        limits = self.get_plan_limits(plan)
        current_bots = len(db.get_user_bots(user_id))
        return current_bots < limits["bots"]

    async def check_group_limits(self, user_id: int, new_group_id: int) -> bool:
        plan = self.get_user_plan(user_id)
        limits = self.get_plan_limits(plan)
        bots = db.get_user_bots(user_id)
        total_groups = 0
        for bot in bots:
            total_groups += len(bot.get("groups", []))
        return total_groups < limits["groups"]

def setup(application: Application):
    handler = SubscriptionHandler()
    application.add_handler(CommandHandler("monabonnement", handler.show_user_plan))