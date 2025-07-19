import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, CallbackQueryHandler
from utils.memory_full import db, UserStates
from utils.code import handle_auth_request
from utils.menu_utils import show_main_menu

logger = logging.getLogger(__name__)

def get_welcome_message(lang='fr', bot_name="votre bot"):
    messages = {
        'fr': f"""
👋🏼 Bienvenue sur {bot_name} !
Votre bot est créé via télésuche.

🧰 Fonctionnalités activées :

🔍 Recherche intelligente
💬 Réponses automatisées (IA)
📊 Analytics temps réel
🛠️ Gestion des abonnements
👥 Gestion des groupes
Etc.

👉🏼 Prochaines étapes : 
Utilisez le bouton ci-dessous.

✨ from @telesuchebot
        """,
        'en': f"""
👋🏼 Welcome to {bot_name} !
Your bot is created via telesuche.

🧰 Activated features:

🔍 Smart search
💬 Automated replies (AI)
📊 Real-time analytics
🛠️ Subscription management
👥 Groups management
Etc.

👉🏼 Next steps: 
Use the button below.

✨ from @telesuchebot
        """,
        'es': f"""
👋🏼 Bienvenido a {bot_name} !
Tu bot es creado via telesuche.

🧰 Funcionalidades activadas:

🔍 Búsqueda inteligente
💬 Respuestas automatizadas (IA)
📊 Análisis en tiempo real
🛠️ Gestión de suscripciones
👥 Gestión de grupos
Etc.

👉🏼 Próximos pasos: 
Usa el botón de abajo.

✨ from @telesuchebot
        """,
        'de': f"""
👋🏼 Willkommen bei {bot_name} !
Ihr Bot wurde über telesuche erstellt.

🧰 Aktivierte Funktionen:

🔍 Intelligente Suche
💬 Automatisierte Antworten (KI)
📊 Echtzeit-Analytik
🛠️ Abonnementverwaltung
👥 Gruppenverwaltung
Etc.

👉🏼 Nächste Schritte: 
Verwenden Sie die Schaltfläche unten.

✨ from @telesuchebot
        """,
        'ru': f"""
👋🏼 Добро пожаловать в {bot_name} !
Ваш бот создан через telesuche.

🧰 Активированные функции:

🔍 Умный поиск
💬 Автоматические ответы (ИИ)
📊 Аналитика в реальном времени
🛠️ Управление подписками
👥 Управление группами
И т.д.

👉🏼 Следующие шаги: 
Используйте кнопку ниже.

✨ from @telesuchebot
        """
    }
    return messages.get(lang, messages['fr'])

def get_language_selection_message(lang='fr'):
    messages = {
        'fr': "Veuillez choisir votre langue :",
        'en': "Please choose your language:",
        'es': "Por favor, elija su idioma:",
        'de': "Bitte wählen Sie Ihre Sprache:",
        'ru': "Пожалуйста, выберите ваш язык:"
    }
    return messages.get(lang, messages['fr'])

async def handle_show_language_options(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        current_lang = db.get_user_language(user_id) or 'fr'

        keyboard = [
            [InlineKeyboardButton("Français 🇫🇷", callback_data="set_lang_fr")],
            [InlineKeyboardButton("English 🇬🇧", callback_data="set_lang_en")],
            [InlineKeyboardButton("Español 🇪🇸", callback_data="set_lang_es")],
            [InlineKeyboardButton("Deutsch 🇩🇪", callback_data="set_lang_de")],
            [InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_ru")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=get_language_selection_message(current_lang),
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Erreur affichage options langue: {e}", exc_info=True)
        await query.message.reply_text("❌ Erreur lors de l'affichage des options de langue.")

async def handle_set_language_callback(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        lang_code = query.data.replace("set_lang_", "")
        user_id = query.from_user.id

        user_data = db.users.get(user_id, {})
        user_data['language'] = lang_code
        db.users[user_id] = user_data
        db.save_to_disk('users', str(user_id), db.users[user_id])

        confirmation_messages = {
            'fr': "✅ Votre langue a été définie sur le français.",
            'en': "✅ Your language has been set to English.",
            'es': "✅ Su idioma ha sido configurado a español.",
            'de': "✅ Ihre Sprache wurde auf Deutsch eingestellt.",
            'ru': "✅ Ваш язык установлен на русский."
        }
        await query.edit_message_text(
            text=confirmation_messages.get(lang_code, confirmation_messages['fr'])
        )
        logger.info(f"Langue utilisateur {user_id} définie sur {lang_code}")

    except Exception as e:
        logger.error(f"Erreur définition langue: {e}", exc_info=True)
        await query.answer("❌ Erreur lors de la définition de la langue.", show_alert=True)
        await query.edit_message_text(
            text="❌ Erreur lors de la définition de la langue. Veuillez réessayer."
        )



async def handle_start(update: Update, context: CallbackContext):
    try:
        user_id = update.effective_user.id
        
        if db.is_new_user(user_id):
            db.users[user_id] = {
                'state': UserStates.INITIAL.value,
                'language': 'fr'
            }
            db.save_to_disk('users', str(user_id), db.users[user_id])
            lang = 'fr'
        else:
            lang = db.get_user_language(user_id) or 'fr'
        
        bot_name = (await context.bot.get_me()).first_name
        welcome_msg = get_welcome_message(lang, bot_name)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Setup", callback_data="trigger_setup")]
        ])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_msg,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Erreur handler start: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Erreur lors de l'initialisation. Veuillez réessayer."
        )
async def handle_setup_command(update: Update, context: CallbackContext):
    await handle_auth_request(update, context)

async def handle_trigger_setup(update: Update, context: CallbackContext):
    await handle_auth_request(update, context)

def get_setup_handlers():
    return [
        CommandHandler("setup", handle_setup_command),
        CallbackQueryHandler(handle_trigger_setup, pattern="^trigger_setup$"),
        CallbackQueryHandler(handle_show_language_options, pattern="^show_lang_options$"),
        CallbackQueryHandler(handle_set_language_callback, pattern="^set_lang_")
    ]




async def setup_user_bot_handlers(application):
    """Configure les handlers pour un bot fils"""
    from utils.user_administrator import register_user_bot_handlers
    
    # Enregistrer d'abord les handlers de base
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CallbackQueryHandler(handle_trigger_setup, pattern="^trigger_setup$"))
    
    # Ensuite les handlers spécifiques de l'administrateur
    await register_user_bot_handlers(application)


