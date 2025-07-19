# bot_deletion_pin.py
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler, filters
from utils.memory_full import db
from utils.security import SecurityManager
from code import AuthManager
from .bot_linking import child_bots

async def handle_final_delete_with_pin(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    entered_pin = update.message.text.strip()
    lang = db.get_user_language(user_id) or 'fr'

    if not context.user_data.get("awaiting_pin_delete"):
        return

    if not AuthManager.validate_pin(entered_pin):
        await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")
        return

    stored_hash = db.get_user_pin(user_id)
    if not stored_hash:
        await update.message.reply_text("❌ Aucun PIN trouvé. Veuillez en créer un via /auth.")
        return

    security = SecurityManager()
    if not security.verify_password(entered_pin, stored_hash):
        await update.message.reply_text("❌ Code PIN incorrect. Veuillez réessayer.")
        return

    bot_username = context.user_data.get("deleting_bot")
    db.mark_bot_for_deletion(user_id, bot_username)

    # Libérer la place (vérification de la suppression effective)
    if bot_username in child_bots:
        try:
            child_bots[bot_username][0].stop_polling()
        except Exception:
            pass
        del child_bots[bot_username]

    db.remove_user_bot(user_id, bot_username)
    context.user_data.pop("deleting_bot", None)
    context.user_data.pop("awaiting_pin_delete", None)

    await update.message.reply_text(
        f"✅ Bot @{bot_username} supprimé avec succès." if lang == 'fr'
        else f"✅ Bot @{bot_username} successfully deleted."
    )

def setup_deletion_pin_handler(application):
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^\d{4}$", ), handle_final_delete_with_pin
    ))

