from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, Application
from datetime import datetime, timedelta
from utils.memory_full import db

pending_captchas = {}

async def send_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for member in update.message.new_chat_members:
        user_id = member.id
        
        # Restreindre l'utilisateur
        await context.bot.restrict_chat_member(
            chat_id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )

        # Préparer le captcha
        key = f"verify:{chat_id}:{user_id}"
        btn = InlineKeyboardButton("✅ Je suis humain", callback_data=key)
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"👋 Bienvenue {member.full_name} ! Veuillez cliquer pour prouver que vous n'êtes pas un bot.",
            reply_markup=InlineKeyboardMarkup([[btn]])
        )
        
        # Sauvegarder
        pending_captchas[key] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "expire_at": datetime.utcnow() + timedelta(minutes=3),
            "message_id": msg.message_id
        }

async def captcha_check_loop(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.utcnow()
    expired = [key for key, val in pending_captchas.items() if val["expire_at"] < now]
    
    for key in expired:
        info = pending_captchas.pop(key)
        try:
            await context.bot.ban_chat_member(info["chat_id"], info["user_id"])
        except Exception:
            pass

async def handle_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    key = query.data
    if key not in pending_captchas:
        return await query.edit_message_text("⛔ Captcha expiré ou invalide.")
    
    info = pending_captchas.pop(key)
    await context.bot.restrict_chat_member(
        info["chat_id"], 
        info["user_id"],
        permissions=ChatPermissions(can_send_messages=True)
    )
    await query.edit_message_text("✅ Vérification réussie, bienvenue !")

def setup(application: Application):
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, send_captcha))
    application.add_handler(CallbackQueryHandler(handle_verification, pattern="^verify:"))
    application.job_queue.run_repeating(captcha_check_loop, interval=30)