# telegram_gemini_5/extensions/handlers/logging.py

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from utils.memory_full import db

async def setlog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await update.message.reply_text(
            "Utilisation: /setlog @nom_du_channel"
        )

    chat_id = update.effective_chat.id
    log_channel = context.args[0]
    # On stocke l'ID du canal de logs
    db.setdefault("log_channel", {})[chat_id] = log_channel

    await update.message.reply_text(
        f"📦 Canal de logs défini: {log_channel}"
    )

async def logdel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    log_target = db.get("log_channel", {}).get(chat_id)

    if not log_target:
        return await update.message.reply_text(
            "Aucun canal de logs défini. Utilisez /setlog."
        )

    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "Répondez à un message à supprimer et logguer."
        )

    # Message originel
    msg = update.message.reply_to_message
    sender = msg.from_user
    text = msg.text or "(non-texte)"

    # Envoi au canal de logs
    await context.bot.send_message(
        chat_id=log_target,
        text=(
            f"🧾 Message supprimé de <b>{sender.full_name}</b>\n"
            f"<code>{text[:400]}</code>"
        ),
        parse_mode="HTML",
    )

    # Suppression et confirmation
    await msg.delete()
    await update.message.reply_text("🗑 Message supprimé et loggé.")

def setup(application: Application) -> None:
    application.add_handler(CommandHandler("setlog", setlog))
    application.add_handler(CommandHandler("logdel", logdel))