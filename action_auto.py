from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes, CommandHandler, Application
from utils.memory_full import db
from datetime import datetime

warnings_store = db.get("warnings_store", {})

async def delwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Répondez à un message pour avertir + supprimer.")
    
    user_id = update.message.reply_to_message.from_user.id
    chat_id = update.effective_chat.id
    warnings_store.setdefault(chat_id, {}).setdefault(user_id, []).append(datetime.utcnow())
    await update.message.reply_to_message.delete()
    await update.message.reply_text("⚠️ Message supprimé + avertissement ajouté.")
    db["warnings_store"] = warnings_store

async def delkick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Répondez à un message pour exclure + supprimer.")
    
    user_id = update.message.reply_to_message.from_user.id
    chat_id = update.effective_chat.id
    await update.message.reply_to_message.delete()
    await context.bot.ban_chat_member(chat_id, user_id)
    await context.bot.unban_chat_member(chat_id, user_id)
    await update.message.reply_text("👢 Utilisateur expulsé + message supprimé.")

async def delban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Répondez à un message pour bannir + supprimer.")
    
    user_id = update.message.reply_to_message.from_user.id
    chat_id = update.effective_chat.id
    await update.message.reply_to_message.delete()
    await context.bot.ban_chat_member(chat_id, user_id)
    await update.message.reply_text("🚫 Utilisateur banni + message supprimé.")

async def delmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("Répondez à un message pour mute + supprimer.")
    
    user_id = update.message.reply_to_message.from_user.id
    chat_id = update.effective_chat.id
    await update.message.reply_to_message.delete()
    await context.bot.restrict_chat_member(
        chat_id, 
        user_id, 
        ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text("🔇 Utilisateur muté + message supprimé.")

def setup(application: Application):
    application.add_handler(CommandHandler("delwarn", delwarn))
    application.add_handler(CommandHandler("delkick", delkick))
    application.add_handler(CommandHandler("delban", delban))
    application.add_handler(CommandHandler("delmute", delmute))