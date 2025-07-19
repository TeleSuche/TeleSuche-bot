from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, Application
from utils.memory_full import db

config_sessions = {}  # user_id: {step, type, data, target_chat_id}

async def config_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("⚙️ Merci d’utiliser cette commande en privé avec moi.")

    keyboard = [
        [InlineKeyboardButton("✉️ Message de bienvenue", callback_data="config:welcome")],
        [InlineKeyboardButton("🔁 Message récurrent", callback_data="config:recurrent")]
    ]
    await update.message.reply_text(
        "Choisissez l’élément à configurer :", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def config_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    section = query.data.split(":")[1]

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
    user_id = update.effective_user.id
    if user_id not in config_sessions:
        return

    session = config_sessions[user_id]
    msg = update.message
    bot_id = str(context.bot.id)

    if session["step"] == "awaiting_text":
        session["data"]["text"] = msg.text
        session["step"] = "awaiting_photo"
        await msg.reply_text(
            "Envoyez-moi une **photo** (ou /skip si aucune).",
            parse_mode="Markdown"
        )

    elif session["step"] == "awaiting_photo":
        if msg.photo:
            session["data"]["photo"] = msg.photo[-1].file_id
        session["step"] = "awaiting_button"
        await msg.reply_text(
            "Envoyez un **bouton** au format `Texte | Lien` ou /skip.",
            parse_mode="Markdown"
        )

    elif session["step"] == "awaiting_button":
        if msg.text and "|" in msg.text:
            label, url = map(str.strip, msg.text.split("|", 1))
            session["data"]["button"] = {"text": label, "url": url}

        section = session["type"]
        key = f"config:{bot_id}:{section}"
        db[key] = session["data"]

        # Si recurrent, enregistrer dans recurrent_timers aussi
        if section.startswith("recurrent"):
            if "recurrent_timers" not in db:
                db["recurrent_timers"] = {}
            if bot_id not in db["recurrent_timers"]:
                db["recurrent_timers"][bot_id] = []
            db["recurrent_timers"][bot_id].append({
                "chat_id": update.effective_chat.id,  # config en privé = admin = ciblage groupe manuellement possible ici
                "config_key": section,
                "delay": 3600  # par défaut 1h (modifiable plus tard)
            })

        del config_sessions[user_id]
        await msg.reply_text("✅ Message sauvegardé.")

async def skip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config_sessions:
        return
    
    session = config_sessions[user_id]
    bot_id = str(context.bot.id)
    section = session["type"]

    if session["step"] == "awaiting_photo":
        session["step"] = "awaiting_button"
        await update.message.reply_text(
            "Envoyez un **bouton** au format `Texte | Lien` ou /skip.",
            parse_mode="Markdown"
        )

    elif session["step"] == "awaiting_button":
        db[f"config:{bot_id}:{section}"] = session["data"]

        if section.startswith("recurrent"):
            if "recurrent_timers" not in db:
                db["recurrent_timers"] = {}
            if bot_id not in db["recurrent_timers"]:
                db["recurrent_timers"][bot_id] = []
            db["recurrent_timers"][bot_id].append({
                "chat_id": update.effective_chat.id,
                "config_key": section,
                "delay": 3600
            })

        del config_sessions[user_id]
        await update.message.reply_text("✅ Message sauvegardé sans bouton.")

async def send_configured(context: ContextTypes.DEFAULT_TYPE, chat_id: int, bot_id: str, section: str):
    key = f"config:{bot_id}:{section}"
    data = db.get(key)
    if not data:
        return
    
    kwargs = {}
    if "button" in data:
        btn = InlineKeyboardButton(data["button"]["text"], url=data["button"]["url"])
        kwargs["reply_markup"] = InlineKeyboardMarkup([[btn]])

    if "photo" in data:
        await context.bot.send_photo(chat_id, photo=data["photo"], caption=data.get("text"), **kwargs)
    else:
        await context.bot.send_message(chat_id, text=data.get("text"), **kwargs)

def setup(application: Application):
    application.add_handler(CommandHandler("config", config_entry))
    application.add_handler(CommandHandler("skip", skip_handler))
    application.add_handler(CallbackQueryHandler(config_callback, pattern="^config:"))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, config_message_handler))