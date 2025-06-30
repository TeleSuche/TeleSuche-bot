# handlers/pin.py

from telegram import Update, ParseMode
from telegram.ext import ContextTypes, CommandHandler, Application
from utils.memory_full import db

pinned_message_id = db.get("pinned_message_id", {})

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    
    if context.args:
        txt = " ".join(context.args)
        msg = await update.message.reply_text(txt, parse_mode=ParseMode.HTML)
        await context.bot.pin_chat_message(chat_id, msg.message_id)
        pinned_message_id[chat_id] = msg.message_id
        await update.message.reply_text("📌 Message envoyé et épinglé.")
    elif update.message.reply_to_message:
        msg_id = update.message.reply_to_message.message_id
        await context.bot.pin_chat_message(chat_id, msg_id)
        pinned_message_id[chat_id] = msg_id
        await update.message.reply_text("📌 Message existant épinglé.")
    else:
        await update.message.reply_text("❗ Utilisez cette commande en réponse ou avec texte.")

async def editpin(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    msg_id = pinned_message_id.get(chat_id)
    if not msg_id:
        return await update.message.reply_text("⚠️ Aucun message épinglé trouvé.")
    new_text = " ".join(context.args)
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg_id,
        text=new_text,
        parse_mode=ParseMode.HTML
    )
    await update.message.reply_text("✏️ Message épinglé modifié.")

async def delpin(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    await context.bot.unpin_chat_message(chat_id)
    pinned_message_id.pop(chat_id, None)
    await update.message.reply_text("❌ Message désépinglé.")

async def pinned(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    msg_id = pinned_message_id.get(chat_id)
    if not msg_id:
        return await update.message.reply_text("Aucun message épinglé enregistré.")
    await context.bot.forward_message(chat_id, chat_id, msg_id)

async def repin(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.effective_chat.id
    msg_id = pinned_message_id.get(chat_id)
    if not msg_id:
        return await update.message.reply_text("Aucun message à repin.")
    await context.bot.unpin_chat_message(chat_id)
    await context.bot.pin_chat_message(chat_id, msg_id, disable_notification=False)
    await update.message.reply_text("🔁 Message réépinglé avec notification.")

# --- SETUP ---

def setup(application: Application): 
    application.add_handler(CommandHandler("pin", pin))
    application.add_handler(CommandHandler("editpin", editpin))
    application.add_handler(CommandHandler("delpin", delpin))
    application.add_handler(CommandHandler("pinned", pinned))
    application.add_handler(CommandHandler("repin", repin))