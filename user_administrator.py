# user_administrator.py
import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from typing import Dict, Callable, List

from utils.memory_full import db, UserStates
from utils.translations import get_text as t
from utils.memory_full import db  # Ajout de l'import global
from extensions.extension import register_bot_fils_extensions
from interface.interface import setup_admin_interfaces
from handlers.groups_handlers import setup_groups_handlers
from utils.database import DatabaseManager
from utils.security import SecurityManager
from utils import message_config
from i18n.translations import TranslationManager

# Import des composants depuis les nouveaux fichiers
from classes import AdminHandler, ModerationHandler, ShopHandler, SubscriptionHandler, ReferralHandler, SearchHandler, UserHandler
from code import AuthManager, SessionManager, active_sessions, UserStateFilter, register_auth_handlers, handle_auth_request, handle_group_auth, request_pin_entry, verify_pin, handle_wrong_pin, grant_access, show_pin_creation_option, save_new_pin, handle_recovery, verify_recovery_email, verify_recovery_code, send_error_message

logger = logging.getLogger(__name__)

# Initialisation des handlers
db_manager = DatabaseManager()
translation_manager = TranslationManager()
security_manager = SecurityManager(db_manager)

admin_handler = AdminHandler(db_manager, translation_manager)
moderation_handler = ModerationHandler(
    db_manager, translation_manager, security_manager)
shop_handler = ShopHandler(db_manager, translation_manager)
subscription_handler = SubscriptionHandler(db_manager)
referral_handler = ReferralHandler(db_manager, translation_manager)
search_handler = SearchHandler(db_manager, translation_manager)
user_handler = UserHandler(db_manager, translation_manager)

async def show_main_menu(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Affiche uniquement le menu principal avec ReplyKeyboard"""
    try:
        # Clavier physique (ReplyKeyboardMarkup)
        main_markup = ReplyKeyboardMarkup(
            keyboard=[
                ["🏠 Menu Admin"],  # Bouton principal
                ["⭐ Achat crédits", "💨 Vitesse de requête"],
                ["Requête en privé", "💳 Portefeuille"],
                ["🆘 Aide"]
            ],
            resize_keyboard=True,
            one_time_keyboard=False
        )

        await context.bot.send_message(
            chat_id,
            "🧭 <b>Menu Principal</b>",
            parse_mode="HTML",
            reply_markup=main_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur affichage menu principal: {e}")
        await context.bot.send_message(chat_id, "❌ Erreur d'affichage du menu.")

async def show_admin_inline_menu(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Affiche uniquement le menu inline d'administration en disposition verticale"""
    try:
        # Menu Inline complet en disposition verticale
        web_app_url = "https://ton-url-connect.com"  # À remplacer par votre URL réelle
        inline_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Ajouter un groupe", callback_data="add_group")],
            [InlineKeyboardButton("📢 Ajouter un canal", callback_data="add_channel")],
            [InlineKeyboardButton("💎 Abonnements", callback_data="manage_subscriptions")],
            [InlineKeyboardButton("🕹️ Menu commandes", callback_data="commands_menu")],
            [InlineKeyboardButton("🔗 Créer un lien", callback_data="create_link")],
            [InlineKeyboardButton("🛒 Créer une boutique", callback_data="create_store")],
            [InlineKeyboardButton("⚙️ Configuration de base", callback_data="setup_basics")],
            [InlineKeyboardButton("👑 Administration", callback_data="admin_panel")],
            [InlineKeyboardButton("⚡ Ajouter du crédit", callback_data="add_credits")],
            [InlineKeyboardButton("🌐 Connecter", web_app=WebAppInfo(url=web_app_url))],
            [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
        ])

        await context.bot.send_message(
            chat_id,
            "🧭 <b>Menu administrateur</b>",
            parse_mode="HTML",
            reply_markup=inline_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur affichage menu admin: {e}")
        await context.bot.send_message(chat_id, "❌ Erreur d'affichage du menu d'administration.")

async def show_full_setup_menu(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Fonction de compatibilité pour l'authentification (affiche le menu principal)"""
    await show_main_menu(chat_id, user_id, context)

async def handle_setup_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère le processus complet de configuration du bot administrateur"""
    try:
        user_id = update.effective_user.id
        
        # Vérification de l'authentification
        if not SessionManager.is_session_active(user_id):
            await handle_auth_request(update, context)
            return

        # Vérification des droits administrateur
        if not security_manager.is_admin(user_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⛔ Accès refusé. Fonction réservée aux administrateurs."
            )
            return

        # Début du processus de configuration
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚙️ Démarrage de la configuration administrateur..."
        )

        # Configuration des options principales
        keyboard = [
            [InlineKeyboardButton("🔧 Configurer les paramètres du bot", callback_data="admin_bot_config")],
            [InlineKeyboardButton("👥 Gérer les utilisateurs", callback_data="admin_manage_users")],
            [InlineKeyboardButton("💰 Gérer les abonnements", callback_data="admin_manage_subs")],
            [InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🛠️ <b>Menu d'administration</b>\nChoisissez une option:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Erreur configuration admin: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Erreur critique lors de la configuration. Contactez le support @TeleSucheSupport."
        )

async def handle_bot_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configuration spécifique du bot"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔄 Mettre à jour le token", callback_data="admin_update_token")],
            [InlineKeyboardButton("✏️ Modifier le nom", callback_data="admin_change_name")],
            [InlineKeyboardButton("🌐 Paramètres de langue", callback_data="admin_lang_settings")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_config_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="⚙️ <b>Configuration du Bot</b>\nSélectionnez une option:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur configuration bot: {e}")
        await update.callback_query.message.reply_text("❌ Erreur lors de la configuration")

async def handle_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestion des utilisateurs"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("👀 Voir tous les utilisateurs", callback_data="admin_view_users")],
            [InlineKeyboardButton("🔍 Rechercher un utilisateur", callback_data="admin_search_user")],
            [InlineKeyboardButton("🛑 Bannir un utilisateur", callback_data="admin_ban_user")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_manage_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="👥 <b>Gestion des Utilisateurs</b>\nSélectionnez une action:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur gestion utilisateurs: {e}")
        await update.callback_query.message.reply_text("❌ Erreur de gestion utilisateur")

async def handle_subscription_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestion des abonnements"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📝 Liste des abonnements", callback_data="admin_list_subs")],
            [InlineKeyboardButton("➕ Ajouter un abonnement", callback_data="admin_add_sub")],
            [InlineKeyboardButton("➖ Retirer un abonnement", callback_data="admin_remove_sub")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_subs_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="💰 <b>Gestion des Abonnements</b>\nSélectionnez une action:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur gestion abonnements: {e}")
        await update.callback_query.message.reply_text("❌ Erreur de gestion des abonnements")

async def handle_stats_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affichage des statistiques"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Récupération des stats depuis la DB
        total_users = db_manager.get_user_count()
        active_users = db_manager.get_active_user_count()
        total_bots = len(db_manager.get_all_admin_bot_tokens())
        
        stats_text = f"""
📊 <b>Statistiques du Système</b>

👥 Utilisateurs totaux: <b>{total_users}</b>
🟢 Utilisateurs actifs: <b>{active_users}</b>
🤖 Bots créés: <b>{total_bots}</b>

📈 Activité dernière semaine:
- Nouvelles inscriptions: <b>42</b>
- Messages traités: <b>1,248</b>
- Revenus générés: <b>€{total_bots * 5:.2f}</b>
"""
        keyboard = [[InlineKeyboardButton("🔙 Retour", callback_data="admin_stats_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=stats_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Erreur affichage stats: {e}")
        await update.callback_query.message.reply_text("❌ Erreur d'affichage des statistiques")

async def register_admin_handlers(application):
    """Enregistre tous les handlers d'administration"""
    # Handlers principaux
    application.add_handler(CallbackQueryHandler(handle_bot_config, pattern="^admin_bot_config$"))
    application.add_handler(CallbackQueryHandler(handle_user_management, pattern="^admin_manage_users$"))
    application.add_handler(CallbackQueryHandler(handle_subscription_management, pattern="^admin_manage_subs$"))
    application.add_handler(CallbackQueryHandler(handle_stats_view, pattern="^admin_stats$"))
    
    # Handlers secondaires
    application.add_handler(CallbackQueryHandler(handle_setup_request, pattern="^admin_config_back$"))
    application.add_handler(CallbackQueryHandler(handle_setup_request, pattern="^admin_manage_back$"))
    application.add_handler(CallbackQueryHandler(handle_setup_request, pattern="^admin_subs_back$"))
    application.add_handler(CallbackQueryHandler(handle_setup_request, pattern="^admin_stats_back$"))

async def configure_bot_commands(application: Application):
    commands = [
        ("setup", "Ouvrir le menu principal"),
        ("recover", "Récupérer accès perdu"),
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
        ("warn", "Avertir un utilisateur"),
        ("start", "Démarrer le bot")
    ]
    await application.bot.set_my_commands(commands)

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour le bouton Retour"""
    try:
        await update.callback_query.message.delete()
    except Exception:
        pass
    await show_main_menu(
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
            "➕ Ajouter au groupe",  # Libellé corrigé
            url=f"https://t.me/{bot_username}?startgroup=true"
        )],
        [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]  # Libellé corrigé
    ])
    
    await context.bot.send_message(
        update.callback_query.message.chat.id,
        f"Pour ajouter ce bot à un groupe:\n1. Allez dans les paramètres du groupe\n2. Sélectionnez 'Ajouter des membres'\n3. Cherchez @{bot_username}",
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
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "➕ Ajouter au canal",  # Libellé corrigé
            url=f"https://t.me/{bot_username}?startchannel=true"
        )],
        [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]  # Libellé corrigé
    ])
    
    await context.bot.send_message(
        update.callback_query.message.chat.id,
        f"Pour ajouter ce bot à un canal:\n1. Allez dans les paramètres du canal\n2. Sélectionnez 'Administrateurs'\n3. Ajoutez @{bot_username} comme administrateur",
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
                text="⚠️ Une erreur s'est produite. Veuillez réessayer ou contactez le support @TeleSucheSupport."
            )
        except Exception:
            pass

async def init_and_start_all_admin_bots_polling():
    """Point d'entrée principal"""
    tokens = user_handler.get_all_admin_bot_tokens()
    if not tokens:
        logger.warning("Aucun token admin trouvé.")
        return

    applications = []
    for token in tokens:
        try:
            application = Application.builder().token(token).build()
            application.add_error_handler(error_handler)
            await register_user_bot_handlers(application)

            import threading
            def run_app():
                application.run_polling()
            
            thread = threading.Thread(target=run_app, daemon=True)
            thread.start()
            applications.append(application)

            logger.info(f"Bot admin démarré avec le token: {token[:6]}...")
        except Exception as e:
            logger.error(f"Erreur démarrage bot admin: {e}")

    return applications

async def register_user_bot_handlers(application: Application):
    """Enregistre les handlers pour un bot utilisateur"""
    try:
        # 1. Enregistrement des handlers d'authentification
        from utils.code import register_auth_handlers
        register_auth_handlers(application)  # IMPORTANT: Ajout des handlers d'authentification
        
        # 2. Enregistrement des commandes de base
        await configure_bot_commands(application)

        # 3. Handlers utilisateur de base
        application.add_handler(CommandHandler("profile", user_handler.profile_command))
        application.add_handler(CommandHandler("me", user_handler.me_command))
        
        # Handler pour le bouton "🏠 Menu Admin"
        application.add_handler(MessageHandler(filters.Regex(r'^🏠 Menu Admin$'), handle_trigger_setup))
        
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
        application.add_handler(CommandHandler("menu", handle_auth_request))
        
        # 4. Handler pour les callbacks - ESSENTIEL!
        application.add_handler(CallbackQueryHandler(handle_callback))

        # 5. Handler spécifique pour le setup
        application.add_handler(CallbackQueryHandler(
            handle_trigger_setup, 
            pattern="^trigger_setup$"
        ))
        
        # Handler pour les messages - DOIT ÊTRE EN DERNIER
        application.add_handler(MessageHandler(filters.ALL, handle_message))
        
        # Intégration des handlers de groupe
        setup_groups_handlers(application)
        
        # Enregistrement des extensions
        register_bot_fils_extensions(application)
        setup_admin_interfaces(application)
        await register_admin_handlers(application)

        logger.info("Handlers du bot utilisateur enregistrés avec succès")
    except Exception as e:
        logger.error(f"Erreur d'enregistrement des handlers: {e}", exc_info=True)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    try:
        if data == "go_back":
            # Supprimer le menu administrateur avant d'afficher le menu principal
            try:
                await query.message.delete()
            except Exception as e:
                logger.error(f"Erreur suppression menu: {e}")
            return await show_main_menu(
                update.effective_chat.id,
                update.effective_user.id,
                context
            )
        elif data == "add_group":
            return await handle_add_group(update, context)
        elif data == "add_channel":
            return await handle_add_channel(update, context)
        elif data == "admin_panel":
            return await handle_setup_request(update, context)
        elif data == "trigger_setup":
            return await handle_setup_request(update, context)

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
    try:
        # Traiter en priorité les états d'authentification
        user_id = update.effective_user.id
        current_state = db.get_user_state(user_id)
        
        logger.info(f"handle_message: user_id={user_id}, current_state={current_state}")
        
        if current_state == UserStates.ASKING_PIN:
            logger.info("Handling PIN verification")
            return await verify_pin(update, context)
        elif current_state == UserStates.CREATING_PIN:
            logger.info("Handling new PIN creation")
            return await save_new_pin(update, context)
        elif current_state == UserStates.RECOVERING_ACCOUNT:
            logger.info("Handling recovery email")
            return await verify_recovery_email(update, context)
        elif current_state == UserStates.VERIFYING_RECOVERY:
            logger.info("Handling recovery code")
            return await verify_recovery_code(update, context)

        # Ensuite, le reste du traitement
        if update.message.chat.type == 'private' and not await security_manager.check_message(update, context):
            return

        if update.message.chat.type in ['group', 'supergroup']:
            await moderation_handler.handle_message(update, context)

        if update.message.document:
            await search_handler.handle_document(update, context)

    except Exception as e:
        logger.error(f"Erreur dans handle_message: {e}")

async def handle_trigger_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.callback_query:
            await update.callback_query.answer()
        
        user_id = update.effective_user.id
        
        # Vérifier si l'utilisateur est authentifié
        if SessionManager.is_session_active(user_id):
            # Afficher le menu inline d'admin en disposition verticale
            await show_admin_inline_menu(update.effective_chat.id, user_id, context)
        else:
            # Si non authentifié, démarrer le processus d'authentification
            await handle_auth_request(update, context)
            
    except Exception as e:
        logger.error(f"Erreur trigger_setup: {e}")
        await send_error_message(update, context, "setup_error")
