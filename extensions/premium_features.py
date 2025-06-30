from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from utils.memory_full import db

PREMIUM_COST = 5  # crédits par recherche premium

def register_premium_features(dispatcher):
    def enable_premium(update: Update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        
        if db.get_user_credits(user_id) >= PREMIUM_COST:
            db.set_premium_status(user_id, True)
            query.answer("✅ Mode Premium activé (5 crédits/semaine)")
        else:
            query.answer("❌ Crédits insuffisants", show_alert=True)

    def set_private_mode(update: Update, context: CallbackContext):
        user_id = update.message.from_user.id
        current_mode = db.get_private_mode(user_id)
        db.set_private_mode(user_id, not current_mode)
        
        status = "activé" if not current_mode else "désactivé"
        update.message.reply_text(f"🔒 Mode privé {status} (résultats en MP)")

    dispatcher.add_handler(CallbackQueryHandler(enable_premium, pattern="^enable_premium$"))
    dispatcher.add_handler(CommandHandler("private", set_private_mode))