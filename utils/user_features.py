import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from utils.memory_full import db, UserStates
from utils.translations import t  # Correction ici

logger = logging.getLogger(__name__)

def get_welcome_message(lang='fr', bot_name="votre bot"):
    """Fonction identique à l'originale"""
    return t('start_welcome', lang, bot_name=bot_name)

async def handle_start(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        lang = db.get_user_language(user_id) or 'fr'
        
        # Initialiser l'utilisateur si nouveau
        if db.is_new_user(user_id):
            db.set_user_language(user_id, lang)
            db.set_user_state(user_id, UserStates.INITIAL)
        
        bot_name = (await context.bot.get_me()).first_name
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Setup", callback_data="trigger_setup")]
        ])

        await update.message.reply_text(
            get_welcome_message(lang, bot_name),
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Start handler error: {e}")
        await update.message.reply_text("❌ Erreur lors de l'initialisation. Veuillez réessayer.")

async def handle_setup_command(update: Update, context: CallbackContext):
    try:
        # Import local pour éviter les dépendances circulaires
        from utils.user_administrator import handle_setup_request
        await handle_setup_request(update, context)
    except Exception as e:
        logger.error(f"Setup command error: {e}")
        await update.message.reply_text("❌ Erreur lors du setup. Veuillez réessayer.")

async def handle_trigger_setup(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if db.is_new_user(user_id):
            db.set_user_state(user_id, UserStates.INITIAL)
        
        # Création d'un faux update pour /setup
        fake_update = Update(
            update_id=update.update_id,
            message=update.effective_message,
            callback_query=None
        )
        setattr(fake_update, 'message', query.message)
        setattr(fake_update.message, 'text', '/setup')
        setattr(fake_update.message, 'from_user', query.from_user)
        
        await handle_setup_command(fake_update, context)
        await query.answer("Configuration démarrée...")
    except Exception as e:
        logger.error(f"Trigger setup error: {e}", exc_info=True)
        await query.answer("❌ Impossible de démarrer", show_alert=True)

def setup(application):
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("setup", handle_setup_command))
    application.add_handler(CallbackQueryHandler(handle_trigger_setup, pattern="^trigger_setup$"))