# code.py
import logging
import random
import string
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    filters,
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler
)
from typing import Dict

from utils.memory_full import db, UserStates
from utils.security import SecurityManager
from utils.menu_utils import show_main_menu as show_menu
from config import config

logger = logging.getLogger(__name__)

active_sessions: Dict[int, datetime] = {}

class AuthManager:
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def validate_pin(pin: str) -> bool:
        return len(pin) == 4 and pin.isdigit()

    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(pattern, email) is not None

class SessionManager:
    @staticmethod
    def start_session(user_id: int):
        active_sessions[user_id] = datetime.now()

    @staticmethod
    def end_session(user_id: int):
        if user_id in active_sessions:
            del active_sessions[user_id]

    @staticmethod
    def is_session_active(user_id: int, timeout_minutes: int = 30) -> bool:
        if user_id not in active_sessions:
            return False

        # Vérifier si la session a expiré
        if (datetime.now() - active_sessions[user_id]).total_seconds() > timeout_minutes * 60:
            del active_sessions[user_id]  # Supprimer la session expirée
            return False
        return True

async def send_error_message(update: Update, context: ContextTypes.DEFAULT_TYPE, error_type: str):
    error_messages = {
        "auth_error": "🔧 Problème d'authentification. Veuillez réessayer.",
        "pin_verification_error": "❌ Erreur lors de la vérification du PIN.",
        "pin_creation_error": "❌ Erreur lors de la création du PIN.",
        "recovery_error": "❌ Impossible de traiter votre demande de récupération.",
        "recovery_code_error": "❌ Erreur lors de la vérification du code.",
        "setup_error": "❌ Erreur lors du démarrage de la configuration."
    }
    message_text = error_messages.get(error_type, "❌ Une erreur est survenue.")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 S'authentifier", callback_data="auth_login")],
        [InlineKeyboardButton("🔓 Code Pin oublié", callback_data="auth_recover")],
        [InlineKeyboardButton("🆘 Aide et support", callback_data="auth_help")]
    ])
    
    # Vérifier si nous avons un contexte valide pour envoyer le message
    if hasattr(context, 'bot') and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{message_text}\n\n🔒 Choisissez une option d'authentification :",
            reply_markup=keyboard
        )
    else:
        logger.error("Impossible d'envoyer le message d'erreur: contexte ou chat invalide")

async def handle_auth_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les actions des boutons d'authentification"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "auth_login":
            await request_pin_entry(update, context)
        elif query.data == "auth_recover":
            await handle_recovery(update, context)
        elif query.data == "auth_help":
            await show_help(update, context)
            
    except Exception as e:
        logger.error(f"Erreur dans handle_auth_buttons: {e}")
        await query.edit_message_text("❌ Erreur lors du traitement")

async def handle_group_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["🔐 Authentification Privée"]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        "🔒 Veuillez ouvrir une conversation privée avec le bot pour vous authentifier.",
        reply_markup=keyboard
    )

async def show_pin_creation_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db.set_user_state(user_id, UserStates.CREATING_PIN)
        
        keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
        message = await context.bot.send_message(
            chat_id,
            "🆕 Aucun PIN configuré. Veuillez créer un nouveau PIN à 4 chiffres :",
            reply_markup=keyboard
        )
        db.set_temp_message_id(user_id, message.message_id)
    except Exception as e:
        logger.error(f"Erreur dans show_pin_creation_option: {e}")
        await send_error_message(update, context, "setup_error")

async def request_pin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db.set_user_state(user_id, UserStates.ASKING_PIN)

        logger.info(f"Requesting PIN entry for user {user_id}")

        keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
        message = await context.bot.send_message(
            chat_id,
            "🔢 Veuillez entrer votre code PIN à 4 chiffres :",
            reply_markup=keyboard
        )
        db.set_temp_message_id(user_id, message.message_id)
    except Exception as e:
        logger.error(f"Erreur dans request_pin_entry: {e}")
        await send_error_message(update, context, "setup_error")

async def verify_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        entered_pin = update.message.text.strip()

        logger.info(f"Received PIN for user {user_id}: {entered_pin}")

        if not AuthManager.validate_pin(entered_pin):
            logger.warning("Invalid PIN format")
            return await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")

        stored_hash = db.get_user_pin(user_id)
        security_manager = SecurityManager()

        if not stored_hash:
            await update.message.reply_text(
                "❌ Aucun PIN configuré. Veuillez en créer un nouveau."
            )
            await show_pin_creation_option(update, context)
            return
        
        if security_manager.verify_password(entered_pin, stored_hash):
            logger.info(f"PIN correct pour l'utilisateur {user_id}")
            SessionManager.start_session(user_id)
            await grant_access(update, context)
        else:
            logger.warning(f"Code PIN incorrect pour l'utilisateur {user_id}")
            await handle_wrong_pin(update, context)
    except Exception as e:
        logger.error(f"Erreur de vérification PIN: {e}")
        await send_error_message(update, context, "pin_verification_error")

async def handle_wrong_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
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
    except Exception as e:
        logger.error(f"Erreur dans handle_wrong_pin: {e}")
        await send_error_message(update, context, "pin_verification_error")

async def grant_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        db.reset_failed_attempts(user_id)
        db.set_user_state(user_id, UserStates.AUTHENTICATED)

        # Afficher le menu principal après authentification
        from utils.user_administrator import show_full_setup_menu
        await show_full_setup_menu(chat_id, user_id, context)
    except Exception as e:
        logger.error(f"Erreur dans grant_access: {e}")
        await context.bot.send_message(chat_id, "❌ Erreur lors de l'accès au menu principal.")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_menu(update, context)

async def save_new_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        new_pin = update.message.text.strip()

        if not AuthManager.validate_pin(new_pin):
            return await update.message.reply_text("❌ Format invalide. 4 chiffres requis.")

        security_manager = SecurityManager()
        hashed_pin = security_manager.hash_password(new_pin)
        db.set_user_pin(user_id, hashed_pin)
        db.set_user_state(user_id, UserStates.AUTHENTICATED)
        SessionManager.start_session(user_id)

        await update.message.reply_text("✅ PIN enregistré avec succès !")
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Erreur de création PIN: {e}")
        await send_error_message(update, context, "pin_creation_error")

async def handle_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db.set_user_state(user_id, UserStates.RECOVERING_ACCOUNT)

        keyboard = ReplyKeyboardMarkup([["❌ Annuler"]], one_time_keyboard=True)
        message = await update.message.reply_text(
            "📧 Entrez l'email associé à votre compte :",
            reply_markup=keyboard
        )
        db.set_temp_message_id(user_id, message.message_id)
    except Exception as e:
        logger.error(f"Erreur dans handle_recovery: {e}")
        await send_error_message(update, context, "recovery_error")

async def verify_recovery_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        email = update.message.text.strip()

        verification_code = AuthManager.generate_verification_code()
        logger.info(f"CODE SIMULÉ (envoyé à {email}): {verification_code}")
        
        db.set_temp_data(user_id, "recovery_code", verification_code)
        db.set_temp_data(user_id, "recovery_email", email)
        db.set_user_state(user_id, UserStates.VERIFYING_RECOVERY)

        await update.message.reply_text(
            f"📩 Un code de vérification a été envoyé à {email}.\n"
            f"CODE SIMULÉ: {verification_code}\n"
            "Entrez ce code ci-dessous :"
        )
    except Exception as e:
        logger.error(f"Erreur d'email de récupération: {e}")
        await send_error_message(update, context, "recovery_error")

async def verify_recovery_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        entered_code = update.message.text.strip()
        stored_code = db.get_temp_data(user_id, "recovery_code")

        if entered_code == stored_code:
            temp_pin = "1234"
            security_manager = SecurityManager()
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
        logger.error(f"Erreur de code de récupération: {e}")
        await send_error_message(update, context, "recovery_code_error")

async def setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 S'authentifier", callback_data="auth_login")],
            [InlineKeyboardButton("🔓 Code Pin oublié", callback_data="auth_recover")],
            [InlineKeyboardButton("🆘 Aide et support", callback_data="auth_help")]
        ])
        await update.message.reply_text(
            "🔒 Configuration requise - Choisissez une option :",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Erreur dans setup_command: {e}")
        await send_error_message(update, context, "setup_error")

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        help_text = (
            "🆘 <b>Aide Authentification</b>\n\n"
            "<b>Guide de fonctionnalité :</b>\n"
            "• Utilisez 'S'authentifier' pour accéder avec votre PIN\n"
            "• 'Code Pin oublié' pour réinitialiser votre accès\n"
            "• Le code de vérification est affiché directement\n\n"
            "<b>Support technique :</b>\n"
            "🗳️ @TeleSucheSupport\n"
            "📬 support@telesuche.com"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Erreur dans show_help: {e}")
        await send_error_message(update, context, "setup_error")

class UserStateFilter(filters.MessageFilter):
    def __init__(self, target_state):
        super().__init__()
        self.target_state = target_state
        self.name = f"UserStateFilter({target_state})"

    def filter(self, message):
        user_id = message.from_user.id
        current_state = db.get_user_state(user_id)
        logger.info(f"UserStateFilter: user_id={user_id}, current_state={current_state}, target_state={self.target_state}")
        return current_state == self.target_state

class AuthenticatedFilter(filters.MessageFilter):
    def __init__(self):
        super().__init__()
        self.name = "AuthenticatedFilter"

    def filter(self, message):
        user_id = message.from_user.id
        return SessionManager.is_session_active(user_id)

async def register_auth_handlers(application: Application):
    # Définir les filtres d'abord
    authenticated_filter = AuthenticatedFilter()
    awaiting_pin_filter = UserStateFilter(UserStates.ASKING_PIN)
    creating_pin_filter = UserStateFilter(UserStates.CREATING_PIN)
    recovering_filter = UserStateFilter(UserStates.RECOVERING_ACCOUNT)
    verifying_filter = UserStateFilter(UserStates.VERIFYING_RECOVERY)
    
    # Maintenant utiliser les filtres définis
    application.add_handler(CommandHandler("start", show_main_menu, filters=authenticated_filter))
    application.add_handler(CommandHandler("menu", show_main_menu, filters=authenticated_filter))
    application.add_handler(CommandHandler("auth", handle_auth_request, filters=~authenticated_filter))
    application.add_handler(CommandHandler("setup", setup_command, filters=~authenticated_filter))
    application.add_handler(CommandHandler("recover", handle_recovery, filters=~authenticated_filter))

    application.add_handler(MessageHandler(
        filters.TEXT & ~authenticated_filter & ~awaiting_pin_filter & ~creating_pin_filter & ~recovering_filter & ~verifying_filter, 
        handle_unauthenticated_message
    ))

    application.add_handler(MessageHandler(filters.TEXT & awaiting_pin_filter, verify_pin))
    application.add_handler(MessageHandler(filters.TEXT & creating_pin_filter, save_new_pin))
    application.add_handler(MessageHandler(filters.TEXT & recovering_filter, verify_recovery_email))
    application.add_handler(MessageHandler(filters.TEXT & verifying_filter, verify_recovery_code))
    
    # Handler pour les boutons d'authentification
    application.add_handler(CallbackQueryHandler(
        handle_auth_buttons, 
        pattern="^auth_login$|^auth_recover$|^auth_help$"
    ))
    
    # Handler pour annuler les opérations
    application.add_handler(MessageHandler(filters.Regex("^❌ Annuler$"), handle_cancel))
    
    # Handlers pour les callbacks d'authentification
    application.add_handler(CallbackQueryHandler(handle_auth_callback, pattern="^auth_login$|^auth_recover$|^auth_help$"))

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        db.set_user_state(user_id, UserStates.IDLE)
        
        # Supprimer le clavier
        await update.message.reply_text(
            "❌ Opération annulée",
            reply_markup=ReplyKeyboardRemove()
        )
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Erreur dans handle_cancel: {e}")
        await send_error_message(update, context, "setup_error")

async def handle_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        logger.info(f"Callback reçu: {query.data}")

        if query.data == "auth_login":
            await request_pin_entry(update, context)
        elif query.data == "auth_recover":
            await handle_recovery(update, context)
        elif query.data == "auth_help":
            await show_help(update, context)
    except Exception as e:
        logger.error(f"Erreur dans handle_auth_callback: {e}")
        await send_error_message(update, context, "setup_error")

async def handle_unauthenticated_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Veuillez vous authentifier pour accéder aux fonctionnalités. Utilisez /auth ou /setup.")
    except Exception as e:
        logger.error(f"Erreur dans handle_unauthenticated_message: {e}")
        await send_error_message(update, context, "auth_error")

async def handle_auth_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Vérifier si c'est un message de groupe ou privé
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            await handle_group_auth(update, context)
        else:
            # Vérifier l'état de l'utilisateur
            user_id = update.effective_user.id
            current_state = db.get_user_state(user_id)
            
            if current_state == UserStates.AUTHENTICATED and SessionManager.is_session_active(user_id):
                # Afficher le menu principal de l'administrateur
                from utils.user_administrator import show_full_setup_menu
                await show_full_setup_menu(update.effective_chat.id, user_id, context)
            else:
                # Si l'utilisateur n'est pas authentifié ou la session a expiré, demander le PIN ou la création du PIN
                if db.get_user_pin(user_id):
                    await request_pin_entry(update, context)
                else:
                    await show_pin_creation_option(update, context)
    except Exception as e:
        logger.error(f"Erreur dans handle_auth_request: {e}")
        await send_error_message(update, context, "auth_error")