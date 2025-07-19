from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from utils.memory_full import db
from .setup_config import send_configured  # Import corrigé


# Chargement des données persistantes
last_seen = db.get("last_seen", {})
message_timeline = db.get("message_timeline", {})
forbidden_words = db.get("forbidden_words", {})


async def on_new_member(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Accueille les nouveaux membres via la fonction send_configured.
    """
    chat_id = update.effective_chat.id
    bot_id = str(context.bot.id)
    await send_configured(context, chat_id, bot_id, "welcome")  # Appel direct


async def on_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Suit l'historique des messages et supprime ceux contenant
    des mots interdits.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    now = datetime.utcnow()

    # Mise à jour des stats
    last_seen.setdefault(chat_id, {})[user_id] = now
    message_timeline.setdefault(chat_id, []).append(now)
    db["last_seen"] = last_seen
    db["message_timeline"] = message_timeline

    # Détection de mots interdits
    text = update.message.text or ""
    # Charger les mots interdits à jour depuis la base de données
    current_forbidden_words = db.get("forbidden_words", {})
    fw_list = current_forbidden_words.get(chat_id, [])
    if any(word.lower() in text.lower() for word in fw_list):
        await update.message.delete()
        await update.message.reply_text("⛔️ Mot interdit détecté.")


def setup(application: Application) -> None:
    """
    Enregistre les handlers pour les nouveaux membres et
    les messages texte (hors commandes).
    """
    application.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            on_new_member
        )
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            on_message
        )
    )