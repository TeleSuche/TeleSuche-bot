import logging
logger = logging.getLogger(__name__)
from datetime import datetime
# user_administrator.py

import logging
import random
import string
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from typing import Dict, Optional, Callable

from utils.memory_full import db, UserStates
from utils.translations import get_text as t
from extensions.extension import register_bot_fils_extensions
from interface.interface import setup_admin_interfaces
from handlers.groups_handlers import setup_groups_handlers  # MODIFICATION IMPORTANTE
from utils.database import DatabaseManager
from utils.security import SecurityManager
from i18n.translations import TranslationManager

MAIN_BOT_USERNAME = os.environ.get("MAIN_BOT_USERNAME", "TeleSucheBot")

logger = logging.getLogger(__name__)

# Gestion des sessions actives
active_sessions: Dict[int, datetime] = {}

class AuthManager:
    """Gestionnaire central d'authentification"""
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """Génère un code de vérification aléatoire"""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def validate_pin(pin: str) -> bool:
        """Valide le format d'un PIN (4 chiffres exactement)"""
        return len(pin) == 4 and pin.isdigit()

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validation basique d'email"""
        return '@' in email and '.' in email.split('@')[-1]

class SessionManager:
    """Gestionnaire des sessions utilisateur"""
    
    @staticmethod
    def start_session(user_id: int):
        """Démarre une nouvelle session pour l'utilisateur"""
        active_sessions[user_id] = datetime.now()

    @staticmethod
    def end_session(user_id: int):
        """Termine la session de l'utilisateur"""
        if user_id in active_sessions:
            del active_sessions[user_id]

    @staticmethod
    def is_session_active(user_id: int, timeout_minutes: int = 30) -> bool:
        """Vérifie si une session est encore valide"""
        if user_id not in active_sessions:
            return False
        return (datetime.now() - active_sessions[user_id]).total_seconds() < timeout_minutes * 60

# Initialisation des handlers personnalisés
db_manager = DatabaseManager()
translation_manager = TranslationManager()
security_manager = SecurityManager(db_manager)

admin_handler = AdminHandler(db_manager, translation_manager)
moderation_handler = ModerationHandler(db_manager, translation_manager, security_manager)
shop_handler = ShopHandler(db_manager, translation_manager)
subscription_handler = SubscriptionHandler(db_manager)
referral_handler = ReferralHandler(db_manager, translation_manager)
search_handler = SearchHandler(db_manager, translation_manager)
user_handler = UserHandler(db_manager, translation_manager)

async def handle_auth_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Point d'entrée principal pour l'authentification"""
    try:
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type

        if chat_type in ['group', 'supergroup']:
            return await handle_group_auth(update, context)

        if SessionManager.is_session_active(user_id):
            return await grant_access(update, context)

        if not security_manager.is_admin(user_id):
            await update.message.reply_text("⚠️ Accès réservé aux administrateurs.")
            return

        user_pin = db.get_user_pin(user_id)
        if user_pin:
            await request_pin_entry(update, context)
        else:
            await show_pin_creation_option(update, context)

    except Exception as e:
        logger.error(f"Auth request error: {e}")
        await send_error_message(update, "auth_error")

async def handle_group_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère l'authentification dans les groupes"""
    keyboard = ReplyKeyboardMarkup(
        [["🔐 Authentification Privée"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "🔒 Veuillez ouvrir une conversation privée avec le bot pour vous authentifier.",
        reply_markup=keyboard
    )

async def request_pin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Demande la saisie du PIN"""
    user_id = update.effective_user.id
    db.set_user_state(user_id, UserStates.AWAITING_PIN)
    
    keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
    message = await update.message.reply_text(
        "🔢 Veuillez entrer votre code PIN à 4 chiffres :",
        reply_markup=keyboard
    )
    db.set_temp_message_id(user_id, message.message_id)

async def verify_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie le PIN saisi"""
    try:
        user_id = update.effective_user.id
        entered_pin = update.message.text.strip()

        if not AuthManager.validate_pin(entered_pin):
            return await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")

        stored_hash = db.get_user_pin(user_id)
        if security_manager.verify_password(entered_pin, stored_hash):
            SessionManager.start_session(user_id)
            await grant_access(update, context)
        else:
            await handle_wrong_pin(update, context)

    except Exception as e:
        logger.error(f"PIN verification error: {e}")
        await send_error_message(update, "pin_verification_error")

async def handle_wrong_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les tentatives de PIN incorrect"""
    user_id = update.effective_user.id
    attempts = db.increment_failed_attempts(user_id)

    if attempts >= 3:
        db.set_user_state(user_id, UserStates.LOCKED_OUT)
        await update.message.reply_text(
            "🔒 Trop de tentatives. Votre compte est temporairement verrouillé.\n"
            "Utilisez /recover pour réinitialiser votre accès."
        )
    else:
        remaining = 3 - attempts
        await update.message.reply_text(
            f"❌ Code incorrect. Il vous reste {remaining} tentative(s).\n"
            "Essayez à nouveau ou utilisez /recover si vous avez oublié votre code."
        )

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accorde l'accès après authentification réussie"""
    user_id = update.effective_user.id
    db.reset_failed_attempts(user_id)
    db.set_user_state(user_id, UserStates.AUTHENTICATED)
    
    await show_main_menu(update, context)
    await update.message.reply_text("✅ Authentification réussie !")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le menu principal après authentification"""
    await show_full_setup_menu(update.message.chat.id, update.effective_user.id, context)

async def show_pin_creation_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les options pour les nouveaux utilisateurs"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Créer un PIN", callback_data="create_pin")],
        [InlineKeyboardButton("🆘 Aide", callback_data="auth_help")]
    ])
    
    await update.message.reply_text(
        "🔒 Vous devez configurer un code PIN pour sécuriser votre compte :",
        reply_markup=keyboard
    )

async def handle_pin_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la création d'un nouveau PIN"""
    user_id = update.callback_query.from_user.id
    db.set_user_state(user_id, UserStates.CREATING_PIN)
    
    keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
    message = await update.callback_query.message.reply_text(
        "🔢 Créez votre code PIN sécurisé (4 chiffres) :",
        reply_markup=keyboard
    )
    db.set_temp_message_id(user_id, message.message_id)
    await update.callback_query.answer()

async def save_new_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enregistre le nouveau PIN"""
    try:
        user_id = update.effective_user.id
        new_pin = update.message.text.strip()

        if not AuthManager.validate_pin(new_pin):
            return await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")

        hashed_pin = security_manager.hash_password(new_pin)
        db.set_user_pin(user_id, hashed_pin)
        db.set_user_state(user_id, UserStates.AUTHENTICATED)
        SessionManager.start_session(user_id)
        
        await update.message.reply_text("✅ PIN enregistré avec succès !")
        await show_main_menu(update, context)

    except Exception as e:
        logger.error(f"PIN creation error: {e}")
        await send_error_message(update, "pin_creation_error")

async def handle_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la récupération de compte"""
    user_id = update.effective_user.id
    db.set_user_state(user_id, UserStates.RECOVERING_ACCOUNT)
    
    keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
    message = await update.message.reply_text(
        "📧 Entrez l'email associé à votre compte :",
        reply_markup=keyboard
    )
    db.set_temp_message_id(user_id, message.message_id)

async def verify_recovery_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie l'email de récupération"""
    try:
        user_id = update.effective_user.id
        email = update.message.text.strip()

        if not AuthManager.validate_email(email):
            return await update.message.reply_text("❌ Format d'email invalide.")

        verification_code = AuthManager.generate_verification_code()
        db.set_temp_data(user_id, "recovery_code", verification_code)
        db.set_temp_data(user_id, "recovery_email", email)
        db.set_user_state(user_id, UserStates.VERIFYING_RECOVERY)
        
        logger.info(f"Code de récupération pour {email}: {verification_code}")
        
        await update.message.reply_text(
            f"📩 Un code de vérification a été envoyé à {email}.\n"
            "Entrez ce code ci-dessous :"
        )

    except Exception as e:
        logger.error(f"Recovery email error: {e}")
        await send_error_message(update, "recovery_error")

async def verify_recovery_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vérifie le code de récupération"""
    try:
        user_id = update.effective_user.id
        entered_code = update.message.text.strip()
        stored_code = db.get_temp_data(user_id, "recovery_code")

        if entered_code == stored_code:
            temp_pin = "0000"
            hashed_temp = security_manager.hash_password(temp_pin)
            db.set_user_pin(user_id, hashed_temp)
            db.clear_temp_data(user_id)
            db.set_user_state(user_id, UserStates.AUTHENTICATED)
            SessionManager.start_session(user_id)
            
            await update.message.reply_text(
                f"🔓 Compte récupéré ! Votre PIN temporaire est : {temp_pin}\n"
                "Changez-le dès que possible dans les paramètres."
            )
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("❌ Code incorrect. Veuillez réessayer.")

    except Exception as e:
        logger.error(f"Recovery code error: {e}")
        await send_error_message(update, "recovery_code_error")

async def send_error_message(update: Update, error_type: str):
    """Envoie un message d'erreur approprié"""
    error_messages = {
        "auth_error": "🔧 Problème d'authentification. Veuillez réessayer.",
        "pin_verification_error": "❌ Erreur lors de la vérification du PIN.",
        "pin_creation_error": "❌ Erreur lors de la création du PIN.",
        "recovery_error": "❌ Impossible de traiter votre demande de récupération.",
        "recovery_code_error": "❌ Erreur lors de la vérification du code."
    }
    
    message = error_messages.get(error_type, "❌ Une erreur est survenue.")
    
    if hasattr(update, 'message'):
        await update.message.reply_text(message)
    elif hasattr(update, 'callback_query'):
        await update.callback_query.message.reply_text(message)

async def register_auth_handlers(application: Application):
    """Enregistre tous les handlers d'authentification"""
    application.add_handler(CommandHandler("auth", handle_auth_request))
    application.add_handler(CommandHandler("recover", handle_recovery))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^\d{4}$') & 
        filters.create(lambda u: db.get_user_state(u.from_user.id) == UserStates.AWAITING_PIN),
        verify_pin
    ))
    
    application.add_handler(CallbackQueryHandler(handle_pin_creation, pattern="^create_pin$"))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^\d{4}$') & 
        filters.create(lambda u: db.get_user_state(u.from_user.id) == UserStates.CREATING_PIN),
        save_new_pin
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.create(
            lambda u: db.get_user_state(u.from_user.id) == UserStates.RECOVERING_ACCOUNT),
        verify_recovery_email
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'^\d{6}$') & 
        filters.create(lambda u: db.get_user_state(u.from_user.id) == UserStates.VERIFYING_RECOVERY),
        verify_recovery_code
    ))
    
    application.add_handler(CallbackQueryHandler(
        lambda u,c: u.callback_query.answer("Contactez @SupportBot pour assistance", show_alert=True),
        pattern="^auth_help$"
    ))

async def configure_bot_commands(application: Application):
    """Configure les commandes visibles dans l'interface Telegram"""
    commands = [
        ("setup", "Ouvrir le menu principal"),
        ("recover", "Récupérer accès perdu"),
        ("groupmenu", "Menu utilisateur groupe"),
        ("profile", "Mon profil"),
        ("me", "Mes informations"),
        ("shop", "Achat de crédits"),
        ("buy", "Acheter un produit"),
        ("credits", "Mes crédits"),
        ("subscribe", "Abonnements"),
        ("premium", "Passer en premium"),
        ("referral", "Parrainage"),
        ("invite", "Générer un lien de parrainage"),
        ("filleuls", "Voir mes filleuls"),
        ("search", "Rechercher dans l'index"),
        ("index", "Indexer un document"),
        ("admin", "Panel administrateur"),
        ("stats", "Statistiques"),
        ("logs", "Logs système"),
        ("kick", "Expulser un utilisateur"),
        ("ban", "Bannir un utilisateur"),
        ("mute", "Réduire au silence"),
        ("unmute", "Retirer le silence"),
        ("warn", "Avertir un utilisateur")
    ]
    await application.bot.set_my_commands(commands)

async def register_user_bot_handlers(application: Application):
    """Point central d'enregistrement des handlers"""
    await configure_bot_commands(application)
    
    # Enregistrement des handlers d'authentification
    await register_auth_handlers(application)
    
    # Handlers utilisateur de base
    application.add_handler(CommandHandler("profile", user_handler.profile_command))
    application.add_handler(CommandHandler("me", user_handler.me_command))
    
    # Handlers boutique
    application.add_handler(CommandHandler("shop", shop_handler.shop_command))
    application.add_handler(CommandHandler("buy", shop_handler.buy_command))
    application.add_handler(CommandHandler("credits", shop_handler.credits_command))
    
    # Handlers abonnement
    application.add_handler(CommandHandler("subscribe", subscription_handler.subscribe_command))
    application.add_handler(CommandHandler("premium", subscription_handler.premium_command))
    
    # Handlers parrainage
    application.add_handler(CommandHandler("referral", referral_handler.referral_command))
    application.add_handler(CommandHandler("invite", referral_handler.invite_command))
    application.add_handler(CommandHandler("filleuls", referral_handler.filleuls_command))
    
    # Handlers recherche
    application.add_handler(CommandHandler("search", search_handler.search_command))
    application.add_handler(CommandHandler("index", search_handler.index_command))
    
    # Handlers admin
    application.add_handler(CommandHandler("admin", admin_handler.admin_panel))
    application.add_handler(CommandHandler("stats", admin_handler.stats_command))
    application.add_handler(CommandHandler("logs", admin_handler.logs_command))
    
    # Handlers de modération (uniquement en inbox)
    def is_private_chat(update: Update):
        return update.message.chat.type == 'private'
    
    application.add_handler(CommandHandler("kick", moderation_handler.kick_command, filters=is_private_chat))
    application.add_handler(CommandHandler("ban", moderation_handler.ban_command, filters=is_private_chat))
    application.add_handler(CommandHandler("mute", moderation_handler.mute_command, filters=is_private_chat))
    application.add_handler(CommandHandler("unmute", moderation_handler.unmute_command, filters=is_private_chat))
    application.add_handler(CommandHandler("warn", moderation_handler.warn_command, filters=is_private_chat))
    
    # Handlers de menu
    application.add_handler(CommandHandler("setup", handle_setup_request))
    application.add_handler(CommandHandler("menu", handle_setup_request))
    application.add_handler(CommandHandler("recover", handle_recovery_command))
    
    # Handler pour les callbacks
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Handler pour les messages
    application.add_handler(MessageHandler(filters.ALL, handle_message))
    
    # MODIFICATION IMPORTANTE : Intégration des handlers de groupe
    setup_groups_handlers(application)  # AJOUT DE CETTE LIGNE
    
    # Enregistrement des extensions
    register_bot_fils_extensions(application)
    setup_admin_interfaces(application)

async def handle_setup_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les requêtes de configuration"""
    return await handle_auth_request(update, context)

async def handle_recovery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour la commande /recover"""
    return await handle_recovery(update, context)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire principal des callbacks"""
    query = update.callback_query
    data = query.data
    
    try:
        if data == "go_back":
            return await handle_back(update, context)
        elif data == "add_group":
            return await handle_add_group(update, context)
        elif data == "add_channel":
            return await handle_add_channel(update, context)
        elif data in ["start_auth", "recover_access", "create_pin", "setup_help"]:
            return
        
        if data.startswith("admin_"):
            user_id = query.from_user.id
            if not security_manager.is_admin(user_id):
                await query.answer("⚠️ Accès réservé aux administrateurs.", show_alert=True)
                return
            await admin_handler.handle_callback(update, context)
        elif data.startswith("shop_"):
            await shop_handler.handle_callback(update, context)
        elif data.startswith("sub_"):
            await subscription_handler.handle_callback(update, context)
        elif data.startswith("ref_"):
            await referral_handler.handle_callback(update, context)
        elif data.startswith("mod_"):
            await moderation_handler.handle_callback(update, context)
        else:
            await user_handler.handle_callback(update, context)
            
    except Exception as e:
        logger.error(f"Erreur dans handle_callback: {e}")
        await query.answer("Une erreur s'est produite.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire principal des messages"""
    try:
        if not await security_manager.check_message(update, context):
            return
        
        if update.message.chat.type in ['group', 'supergroup']:
            await moderation_handler.handle_message(update, context)
        
        if update.message.document:
            await search_handler.handle_document(update, context)
        
    except Exception as e:
        logger.error(f"Erreur dans handle_message: {e}")

async def show_full_setup_menu(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le menu principal complet"""
    try:
        main_markup = ReplyKeyboardMarkup(
            [
                ["🏠 Accueil", "⚙️ Paramètres"],
                ["📊 Statistiques", "💳 Portefeuille"],
                ["🛒 Boutique", "💎 Abonnements"]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        web_app_url = "https://ton-url-connect.com"
        inline_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Ajouter un groupe", callback_data="add_group"),
                InlineKeyboardButton("📢 Ajouter un canal", callback_data="add_channel")
            ],
            [
                InlineKeyboardButton("💎 Abonnements", callback_data="sub_menu"),
                InlineKeyboardButton("🕹️ Menu commandes", callback_data="commands_menu")
            ],
            [
                InlineKeyboardButton("🔗 Créer un lien", callback_data="create_link"),
                InlineKeyboardButton("🛒 Boutique", callback_data="shop_menu"),
                InlineKeyboardButton("🏬 Store", callback_data="store_menu")
            ],
            [
                InlineKeyboardButton("⚙️ Configuration de base", callback_data="setup_basics"),
                InlineKeyboardButton("👑 Administration", callback_data="admin_panel")
            ],
            [
                InlineKeyboardButton("🔙 Retour", callback_data="go_back"),
                InlineKeyboardButton("⚡ Ajouter du crédit", callback_data="add_credits"),
                InlineKeyboardButton("🌐 Connecter", web_app=WebAppInfo(url=web_app_url))
            ]
        ])

        await context.bot.send_message(
            chat_id,
            "🧭 <b>Menu Principal</b> - Sélectionnez une option :",
            parse_mode="HTML",
            reply_markup=main_markup
        )
        
        await context.bot.send_message(
            chat_id,
            "🧭 <b>Menu administrateur - Gestion complète de votre bot</b>",
            parse_mode="HTML",
            reply_markup=inline_markup
        )

        SessionManager.start_session(user_id)
        
    except Exception as e:
        logger.error(f"Menu display error: {e}")
        await context.bot.send_message(chat_id, "❌ Erreur d'affichage du menu. Veuillez réessayer.")

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour le bouton Retour"""
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass
    await show_full_setup_menu(
        update.callback_query.message.chat.id, 
        update.callback_query.from_user.id, 
        context
    )
    await update.callback_query.answer()

async def handle_add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour ajouter un groupe"""
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass

    bot_username = (await context.bot.get_me()).username
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Ajouter ce bot à un groupe", 
            url=f"https://t.me/{bot_username}?startgroup=true"
        )],
        [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
    ])
    await context.bot.send_message(
        update.callback_query.message.chat.id,
        "➕ Utilisez le bouton ci-dessous pour ajouter ce bot à un groupe :",
        reply_markup=keyboard
    )
    await update.callback_query.answer()

async def handle_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour ajouter un canal"""
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass

    bot_username = (await context.bot.get_me()).username
    instructions = (
        "📢 <b>Ajouter ce bot à votre canal</b>\n\n"
        "1. Cliquez sur le bouton ci-dessous\n"
        "2. Sélectionnez votre canal\n"
        "3. Donnez les droits d'administrateur au bot\n"
        "4. Envoyez un message dans le canal pour finaliser"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Ajouter à un canal", 
            url=f"https://t.me/{bot_username}?startchannel=true"
        )],
        [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
    ])
    await context.bot.send_message(
        update.callback_query.message.chat.id,
        instructions,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await update.callback_query.answer()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire d'erreurs global"""
    logger.error(f"Exception: {context.error}")
    
    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Une erreur s'est produite. Veuillez réessayer."
            )
        except Exception:
            pass

async def init_and_start_all_admin_bots_polling():
    """Point d'entrée principal"""
    for token in db.get_all_admin_bot_tokens():
        try:
            application = Application.builder().token(token).build()
            application.add_error_handler(error_handler)
            await register_user_bot_handlers(application)
            
            import threading
            def run_app():
                application.run_polling()
            
            thread = threading.Thread(target=run_app, daemon=True)
            thread.start()
            
            logger.info(f"Bot démarré avec le token: {token[:6]}...")
        except Exception as e:
            logger.error(f"Erreur démarrage bot: {e}")