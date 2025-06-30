# config.py - Configuration centrale et gestion des messages configurés

import os
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application
from utils.memory_full import db

class BotConfig:
    """Configuration principale de l'application"""
    
    # 1. Paramètres de base
    BOT_TOKEN = os.getenv("BOT_TOKEN", "7794487631:AAG3F3i7IIuYMT_tR18Ma5P-bdBV_VKa5-A")
    MAIN_BOT_USERNAME = os.getenv("MAIN_BOT_USERNAME", "TeleSucheBot")
    ADMIN_IDS = [1263139963]  # À remplacer par vos IDs admin
    
    # 2. Configuration base de données
    DB_CONFIG = {
        'host': os.getenv("DB_HOST", "localhost"),
        'port': int(os.getenv("DB_PORT", 27017)),
        'name': os.getenv("DB_NAME", "telegram_bot_db")
    }
    
    # 3. Paramètres des messages configurables
    MESSAGE_TYPES = {
        'welcome': {
            'description': "Message de bienvenue",
            'has_photo': True,
            'has_button': True
        },
        'recurrent': {
            'description': "Message récurrent",
            'has_photo': True,
            'has_button': True,
            'default_delay': 3600  # 1 heure
        }
    }

# Gestion des sessions de configuration
config_sessions = {}  # Format: {user_id: {'step': str, 'type': str, 'data': dict}}

async def config_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Point d'entrée pour la configuration"""
    if update.effective_chat.type != "private":
        return await update.message.reply_text("⚙️ Merci d'utiliser cette commande en privé.")
    
    keyboard = [
        [InlineKeyboardButton(
            f"✉️ {BotConfig.MESSAGE_TYPES['welcome']['description']}", 
            callback_data="config:welcome"
        )],
        [InlineKeyboardButton(
            f"🔁 {BotConfig.MESSAGE_TYPES['recurrent']['description']}", 
            callback_data="config:recurrent"
        )]
    ]
    await update.message.reply_text(
        "Choisissez l'élément à configurer :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def config_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la sélection du type de message"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    section = query.data.split(":")[1]

    if section not in BotConfig.MESSAGE_TYPES:
        return await query.edit_message_text("❌ Type de configuration invalide.")
    
    config_sessions[user_id] = {
        "step": "awaiting_text",
        "type": section,
        "data": {},
        "target_chat_id": None
    }
    await query.edit_message_text(
        f"Envoyez-moi le **texte** pour le message {section}.",
        parse_mode="Markdown"
    )

async def config_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les étapes de configuration"""
    user_id = update.effective_user.id
    if user_id not in config_sessions:
        return

    session = config_sessions[user_id]
    msg = update.message
    msg_type = session["type"]
    config_data = BotConfig.MESSAGE_TYPES[msg_type]

    if session["step"] == "awaiting_text":
        session["data"]["text"] = msg.text
        session["step"] = "awaiting_photo" if config_data["has_photo"] else "awaiting_button"
        next_prompt = "Envoyez-moi une **photo** (ou /skip si aucune)." if config_data["has_photo"] else "Envoyez un **bouton** au format `Texte | Lien` ou /skip."
        await msg.reply_text(next_prompt, parse_mode="Markdown")

    elif session["step"] == "awaiting_photo" and msg.photo:
        session["data"]["photo"] = msg.photo[-1].file_id
        session["step"] = "awaiting_button"
        await msg.reply_text(
            "Envoyez un **bouton** au format `Texte | Lien` ou /skip.",
            parse_mode="Markdown"
        )

    elif session["step"] == "awaiting_button" and msg.text and "|" in msg.text:
        label, url = map(str.strip, msg.text.split("|", 1))
        session["data"]["button"] = {"text": label, "url": url}
        await save_configuration(update, context, session)

async def skip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les étapes skipées"""
    user_id = update.effective_user.id
    if user_id not in config_sessions:
        return
    
    session = config_sessions[user_id]
    msg_type = session["type"]
    
    if session["step"] == "awaiting_photo":
        session["step"] = "awaiting_button"
        await update.message.reply_text(
            "Envoyez un **bouton** au format `Texte | Lien` ou /skip.",
            parse_mode="Markdown"
        )
    else:
        await save_configuration(update, context, session)

async def save_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Sauvegarde finale de la configuration"""
    bot_id = str(context.bot.id)
    section = session["type"]
    key = f"config:{bot_id}:{section}"
    
    db[key] = session["data"]
    
    if section == "recurrent":
        if "recurrent_timers" not in db:
            db["recurrent_timers"] = {}
        if bot_id not in db["recurrent_timers"]:
            db["recurrent_timers"][bot_id] = []
        
        db["recurrent_timers"][bot_id].append({
            "chat_id": update.effective_chat.id,
            "config_key": section,
            "delay": BotConfig.MESSAGE_TYPES['recurrent']['default_delay']
        })
    
    del config_sessions[update.effective_user.id]
    await update.message.reply_text("✅ Configuration sauvegardée avec succès !")

async def send_configured_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, bot_id: str, message_type: str):
    """Envoie un message préconfiguré"""
    key = f"config:{bot_id}:{message_type}"
    data = db.get(key)
    if not data:
        return
    
    kwargs = {}
    if "button" in data:
        btn = InlineKeyboardButton(
            data["button"]["text"], 
            url=data["button"]["url"]
        )
        kwargs["reply_markup"] = InlineKeyboardMarkup([[btn]])
    
    if "photo" in data:
        await context.bot.send_photo(
            chat_id,
            photo=data["photo"],
            caption=data.get("text", ""),
            **kwargs
        )
    else:
        await context.bot.send_message(
            chat_id,
            text=data.get("text", ""),
            **kwargs
        )

def setup_config_handlers(application: Application):
    """Configure les handlers pour la configuration"""
    application.add_handler(CommandHandler("config", config_entry))
    application.add_handler(CommandHandler("skip", skip_handler))
    application.add_handler(CallbackQueryHandler(
        config_callback, 
        pattern="^config:"
    ))
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO, 
        config_message_handler
    ))