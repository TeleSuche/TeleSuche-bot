from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, Application from datetime import datetime
from utils.memory_full import db from . import config  # import send_configured

Track last_seen + timeline for stats

last_seen = db.get("last_seen", {}) message_timeline = db.get("message_timeline", {}) forbidden_words = db.get("forbidden_words", {})

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE): chat_id = update.effective_chat.id bot_id = str(context.bot.id) await config.send_configured(context, chat_id, bot_id, "welcome")

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE): chat_id = update.effective_chat.id user_id = update.effective_user.id now = datetime.utcnow()

# Stats tracking
last_seen.setdefault(chat_id, {})[user_id] = now
message_timeline.setdefault(chat_id, []).append(now)
db["last_seen"] = last_seen
db["message_timeline"] = message_timeline

# Interdits
fw = forbidden_words.get(chat_id, [])
if any(w.lower() in update.message.text.lower() for w in fw):
    await update.message.delete()
    await update.message.reply_text("⛔️ Mot interdit détecté.")

--- SETUP ---

def setup(application: Application): application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member)) application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
