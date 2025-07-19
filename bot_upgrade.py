# === 1. handlers/bot_upgrade.py ===
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters
from utils.memory_full import db, UserStates
from utils.security import SecurityManager
from subscriptions import PLANS
from code import AuthManager

async def ask_upgrade_pin(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = db.get_user_language(user_id) or 'fr'

    db.set_user_state(user_id, UserStates.ASKING_PIN)
    context.user_data['upgrade_requested'] = True

    await query.message.reply_text(
        "🔐 Veuillez entrer votre code PIN à 4 chiffres pour confirmer la mise à niveau :"
    )

async def confirm_upgrade_with_pin(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    pin = update.message.text.strip()
    lang = db.get_user_language(user_id) or 'fr'

    if not AuthManager.validate_pin(pin):
        await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")
        return

    stored_hash = db.get_user_pin(user_id)
    if not stored_hash:
        await update.message.reply_text("❌ Aucun PIN trouvé. Veuillez en créer un via /auth.")
        return

    security = SecurityManager()
    if not security.verify_password(pin, stored_hash):
        await update.message.reply_text("❌ PIN incorrect. Veuillez réessayer.")
        return

    db.set_user_state(user_id, UserStates.AUTHENTICATED)

    # Affichage des plans disponibles pour mise à niveau
    text = (
        "🆙 <b>Mise à niveau de votre abonnement</b>

"
        "Sélectionnez un plan pour voir les détails :"
    )
    keyboard = [
        [InlineKeyboardButton(plan["label"], callback_data=f"plan_details:{pid}")]
        for pid, plan in PLANS.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")])

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

    context.user_data.pop('upgrade_requested', None)


def setup_upgrade_handlers(application):
    application.add_handler(CallbackQueryHandler(ask_upgrade_pin, pattern="^upgrade_plan$"))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^\d{4}$"), confirm_upgrade_with_pin
    ))