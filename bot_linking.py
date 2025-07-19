import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ApplicationBuilder

from typing import Dict
from datetime import datetime

from utils.memory_full import db, UserStates
from utils.api_client import sync_validate_bot_token
from utils.user_features import get_welcome_message
from config import config
from utils.keyboards import KeyboardManager
from utils.menu_utils import show_main_menu
from utils.security import SecurityManager



PDG_USER_ID = config.PDG_USER_ID
child_bots: Dict[str, Application] = {}
pending_deletions = {}

def init_child_bot(token: str, bot_username: str):
    """Initialise et démarre un bot fils avec python-telegram-bot"""
    try:
        application = (
            ApplicationBuilder()
            .token(token)
            .connect_timeout(30)
            .read_timeout(30)
            .pool_timeout(30)
            .build()
        )
        
        # Les handlers seront enregistrés avant le démarrage du polling
        # La fonction register_user_bot_handlers est asynchrone et sera appelée dans la tâche asyncio
        
        return application
    except Exception as e:
        logger.error(f"Erreur initialisation bot fils: {e}")
        return None

def get_plan_limits(plan: str) -> Dict[str, int]:
    """Retourne les limites selon le plan"""
    limits = {
        "sub_basic": {"bots": 1, "groups": 2, "channels": 1},
        "sub_avance": {"bots": 2, "groups": 5, "channels": 2},
        "sub_premium": {"bots": 3, "groups": 10, "channels": 3},
        "sub_pro": {"bots": 5, "groups": 20, "channels": 5},
        "sub_ultime": {"bots": float("inf"), "groups": float("inf"), "channels": float("inf")}
    }
    return limits.get(plan, limits["sub_basic"])

async def check_bot_limits(user_id: int) -> bool:
    """Vérifie si l'utilisateur peut ajouter un nouveau bot"""
    plan = db.get_user_plan(user_id) or "sub_basic"
    user_bots = db.get_user_bots(user_id)
    plan_limits = get_plan_limits(plan)
    
    # Check for trial period
    trial_end_date = db.get_user_trial_end_date(user_id)
    if trial_end_date and datetime.now() < trial_end_date:
        # During trial, allow up to 10 bots
        if len(user_bots) >= 10:
            return False
    else:
        # After trial, apply plan limits
        if len(user_bots) >= plan_limits["bots"]:
            return False
    return True

async def check_group_limits(user_id: int, new_group_id: int = 0) -> bool:
    """Vérifie les limites de groupes"""
    plan = db.get_user_plan(user_id) or "sub_basic"
    user_bots = db.get_user_bots(user_id)
    plan_limits = get_plan_limits(plan)
    
    total_groups = sum(len(bot.get("groups", [])) for bot in user_bots)
    if new_group_id > 0:
        total_groups += 1
    
    if total_groups >= plan_limits["groups"]:
        return False
    return True

class BotLinkingManager:



    @staticmethod
    async def show_bot_info(update: Update, context: CallbackContext):
        """Affiche les informations détaillées d'un bot."""
        try:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            bot_username = query.data.split(":")[1]

            user_bots = db.get_user_bots(user_id)
            selected_bot = next((bot for bot in user_bots if bot.get("bot_username") == bot_username), None)

            if not selected_bot:
                await query.edit_message_text("❌ Bot non trouvé." if lang == 'fr' else "❌ Bot not found.")
                return

            bot_name = selected_bot.get("bot_name", "N/A")
            bot_token = selected_bot.get("token", "N/A")
            creation_time = selected_bot.get("creation_time", "N/A")
            # bot_id n'est pas stocké dans db.save_user_bot, donc il sera N/A
            # Si nécessaire, il faudrait modifier save_user_bot pour stocker bot_id
            bot_id = "N/A"

            text = (
                f"<b>🤖 Informations détaillées du bot :</b>\n\n"
                f"<b>Nom :</b> {bot_name}\n"
                f"<b>Nom d'utilisateur :</b> @{bot_username}\n"
                f"<b>ID du bot :</b> {bot_id}\n"
                f"<b>Token :</b> <code>{bot_token}</code>\n"
                f"<b>Date de création :</b> {creation_time}\n\n"
                f"Pour des raisons de sécurité, ne partagez jamais votre token !"
                if lang == 'fr' else
                f"<b>🤖 Detailed Bot Information:</b>\n\n"
                f"<b>Name:</b> {bot_name}\n"
                f"<b>Username:</b> @{bot_username}\n"
                f"<b>Bot ID:</b> {bot_id}\n"
                f"<b>Token:</b> <code>{bot_token}</code>\n"
                f"<b>Creation Date:</b> {creation_time}\n\n"
                f"For security reasons, never share your token!"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Retour aux détails du bot" if lang == 'fr' else "🔙 Back to bot details", callback_data=f"bot_detail:{bot_username}")]
            ])

            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Erreur dans show_bot_info: {e} [ERR_BLM_001]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_001)")



    @staticmethod
    async def handle_my_bots(update: Update, context: CallbackContext):
        """Gère la commande /mybots pour afficher les bots de l'utilisateur"""
        try:
            if update.message:
                user_id = update.message.from_user.id
            else:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
                
            lang = db.get_user_language(user_id) or 'fr'
            user_bots = db.get_user_bots(user_id)
            
            if not user_bots:
                text = "🤖 Vous n'avez aucun bot connecté." if lang == 'fr' else "🤖 You don't have any connected bots."
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Créer un bot" if lang == 'fr' else "➕ Create a bot", callback_data="createbot")]
                ])
            else:
                text = "🤖 Vos bots connectés :" if lang == 'fr' else "🤖 Your connected bots:"
                keyboard_buttons = []
                
                for bot in user_bots:
                    bot_username = bot.get("bot_username")
                    bot_name = bot.get("bot_name")
                    if bot_username and bot_name:
                        keyboard_buttons.append([
                            InlineKeyboardButton(f"🤖Bot : @{bot_username}", callback_data=f"bot_detail:{bot_username}")
                        ])
                
                keyboard_buttons.append([
                    InlineKeyboardButton("➕ Ajouter un bot" if lang == 'fr' else "➕ Add a bot", callback_data="createbot"),
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data="back_to_main")
                ])
                keyboard = InlineKeyboardMarkup(keyboard_buttons)
            
            if update.message:
                await update.message.reply_text(text, reply_markup=keyboard)
            else:
                await query.edit_message_text(text, reply_markup=keyboard)
                
        except Exception as e:
            logger.error(f"Erreur dans handle_my_bots: {e} [ERR_BLM_002]", exc_info=True)
            if update.callback_query:
                await update.callback_query.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_002)")
            else:
                await update.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_002)")

    @staticmethod
    async def handle_bot_detail(update: Update, context: CallbackContext):
        """Affiche les détails d'un bot spécifique et les options de gestion."""
        try:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            bot_identifier = query.data.split(":")[1]

            user_bots = db.get_user_bots(user_id)
            selected_bot = next((bot for bot in user_bots if bot.get("bot_username") == bot_identifier), None)
            if not selected_bot:
                await query.edit_message_text("❌ Bot non trouvé." if lang == 'fr' else "❌ Bot not found.")
                return

            bot_name = selected_bot.get("bot_name", "Bot")
            bot_username = selected_bot.get("bot_username", "unknown")
            creation_time = selected_bot.get("creation_time", "N/A")

            text = (
                f"🤖 <b>Détails du bot :</b>\n\n"
                f"Nom : {bot_name}\n"
                f"@{bot_username}\n"
                f"Créé le : {creation_time}\n\n"
                f"Que souhaitez-vous faire avec ce bot ?"
                if lang == 'fr' else
                f"🤖 <b>Bot details:</b>\n\n"
                f"Name: {bot_name}\n"
                f"@{bot_username}\n"
                f"Created on: {creation_time}\n\n"
                f"What would you like to do with this bot?"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("ℹ️ Info du bot" if lang == 'fr' else "ℹ️ Bot Info", callback_data=f"show_bot_info:{bot_username}")],
                [InlineKeyboardButton("🗑️ Supprimer le bot" if lang == 'fr' else "🗑️ Delete bot", callback_data=f"ask_delete_bot:{bot_username}")],
                [InlineKeyboardButton("🔙 Retour à Mes bots" if lang == 'fr' else "🔙 Back to My bots", callback_data="my_bots")]
            ])

            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Erreur dans handle_bot_detail: {e} [ERR_BLM_003]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_003)")

    @staticmethod
    async def handle_main_start(update: Update, context: CallbackContext):
        """Handler /start pour le bot principal"""
        try:
            user_id = update.effective_user.id
            
            if db.is_new_user(user_id):
                db.users[user_id] = {
                    'state': UserStates.INITIAL.value,
                    'language': 'fr',
                    'trial_end_date': (datetime.now() + timedelta(days=14)).isoformat()
                }
                db.save_to_disk('users', {str(user_id): db.users[user_id]})
                await BotLinkingManager.show_language_options(update, context)
            else:
                await show_main_menu(update, context)

        except Exception as e:
            logger.error(f"Erreur dans handle_main_start: {e} [ERR_BLM_004]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de l\"initialisation. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_004)")

    @staticmethod
    async def show_language_options(update: Update, context: CallbackContext):
        """Affiche les options de langue"""
        try:
            if update.message:
                user_id = update.message.from_user.id
                lang = 'fr'  # Default language
            else:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
                lang = db.get_user_language(user_id) or 'fr'
            
            text = (
                "🌐 Veuillez choisir votre langue préférée :"
                if lang == 'fr' else
                "🌐 Please choose your preferred language:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🇫🇷 Français", callback_data="setlang_fr"),
                    InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
                    InlineKeyboardButton("🇪🇸 Español", callback_data="setlang_es")
                ],
                [
                    InlineKeyboardButton("🇩🇪 Deutsch", callback_data="setlang_de"),
                    InlineKeyboardButton("🇨🇳 中文", callback_data="setlang_zh"),
                    InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="setlang_hi")
                ],
                [
                    InlineKeyboardButton("🇯🇵 日本語", callback_data="setlang_ja"),
                    InlineKeyboardButton("🇰🇷 한국어", callback_data="setlang_ko"),
                    InlineKeyboardButton("🇹🇭 ไทย", callback_data="setlang_th")
                ],
                [
                    InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
                    InlineKeyboardButton("🇵🇹 Português", callback_data="setlang_pt"),
                    InlineKeyboardButton("🇮🇹 Italiano", callback_data="setlang_it")
                ],
                [
                    InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", 
                                       callback_data="back_to_main")
                ]
            ]
            
            if update.callback_query:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Erreur dans show_language_options: {e} [ERR_BLM_005]", exc_info=True)    @staticmethod
    async def set_language(update: Update, context: CallbackContext):
        """Définit la langue de l'utilisateur"""
        try:
            query = update.callback_query
            await query.answer()
            lang_code = query.data.split("_")[1]
            user_id = query.from_user.id
            
            db.set_user_language(user_id, lang_code)
            
            lang_names = {
                'fr': "Français",
                'en': "English",
                'es': "Español", 
                'de': "Deutsch",
                'zh': "中文",
                'hi': "हिन्दी",
                'ja': "日本語",
                'ko': "한국어",
                'th': "ไทย",
                'ru': "Русский",
                'pt': "Português",
                'it': "Italiano"
            }
            
            confirmation = (
                f"✅ Langue définie sur {lang_names[lang_code]}"
                if lang_code == 'fr' else
                f"✅ Language set to {lang_names[lang_code]}"
            )
            
            await query.edit_message_text(
                confirmation,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "✅ Commencer" if lang_code == 'fr' else "✅ Start",
                        callback_data="terms_accepted"
                    )]
                ])
            )
        except Exception as e:
            logger.error(f"Erreur dans set_language: {e} [ERR_BLM_006]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_006)")
    @staticmethod
    async def accept_terms(update: Update, context: CallbackContext):
        """Affiche et gère l'acceptation des conditions"""
        try:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            terms_text = (
                "📜 <b>Conditions d'utilisation</b>\n\n"
                "1. Confidentialité : Vos données sont cryptées\n"
                "2. Utilisation : Interdiction de spam\n"
                "3. Sécurité : Ne partagez pas vos tokens\n\n"
                "En continuant, vous acceptez nos conditions."
                if lang == 'fr' else
                "📜 <b>Terms of Service</b>\n\n"
                "1. Privacy: Your data is encrypted\n"
                "2. Usage: No spamming allowed\n"
                "3. Security: Don't share your tokens\n\n"
                "By continuing, you accept our terms."
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ J'accepte" if lang == 'fr' else "✅ I Accept", 
                                     callback_data="terms_accepted")],
                [InlineKeyboardButton("❌ Refuser" if lang == 'fr' else "❌ Decline", 
                                    callback_data="terms_declined")]
            ]
            
            await query.edit_message_text(
                terms_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur dans accept_terms: {e} [ERR_BLM_007]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_007)")
    @staticmethod
    async def terms_accepted(update: Update, context: CallbackContext):
        """Passe au menu principal après acceptation"""
        try:
            query = update.callback_query
            await query.answer()
            db.save_terms_acceptance(query.from_user.id)
            await show_main_menu(update, context)
        except Exception as e:
            logger.error(f"Erreur dans terms_accepted: {e} [ERR_BLM_008]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_008)")
    @staticmethod
    async def start_bot_creation(update: Update, context: CallbackContext):
        """Démarre le processus de création de bot"""
        try:
            if update.message:
                user_id = update.message.from_user.id
            else:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
                
            lang = db.get_user_language(user_id) or 'fr'
            
            text = (
                "🤖 Création de votre bot personnel\n\n"
                "Avez-vous déjà un bot Telegram existant ?"
                if lang == 'fr' else
                "🤖 Creating your bot assistant\n\n"
                "Do you already have an existing Telegram bot?"
            )
            
            if update.message:
                await update.message.reply_text(
                    text, 
                    reply_markup=KeyboardManager.bot_creation_options(lang)
                )
            else:
                await query.edit_message_text(
                    text, 
                    reply_markup=KeyboardManager.bot_creation_options(lang)
                )
        except Exception as e:
            logger.error(f"Erreur dans start_bot_creation: {e} [ERR_BLM_009]", exc_info=True)
            if update.callback_query:
                await update.callback_query.message.reply_text("❌ Erreur lors du démarrage. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_009)")
            else:
                await update.message.reply_text("❌ Erreur lors du démarrage. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_009)")

    @staticmethod
    async def handle_has_token_yes(update: Update, context: CallbackContext):
        """Gère la réponse 'Oui, j'ai un token'"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'

            security_advice = (
                "🔐 Conseil de sécurité :\n"
                "1. Ne partagez jamais votre token publiquement\n"
                "2. Utilisez /revoke dans @BotFather si compromis\n"
                "3. Notre système le chiffrera automatiquement"
                if lang == 'fr' else
                "🔐 Security advice:\n"
                "1. Never share your token publicly\n"
                "2. Use /revoke in @BotFather if compromised\n"
                "3. Our system will encrypt it automatically"
            )

            prompt = "Parfait ! Veuillez m'envoyer votre token :" if lang == 'fr' else "Perfect! Please send me your token:"
            await query.edit_message_text(f"✅ {prompt}\n\n{security_advice}", parse_mode="Markdown")
            context.user_data["awaiting_token"] = True
        except Exception as e:
            logger.error(f"Erreur dans handle_has_token_yes: {e} [ERR_BLM_010]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_010)")

    @staticmethod
    async def handle_has_token_no(update: Update, context: CallbackContext):
        """Gère la réponse 'Non, je n'ai pas de token'"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'

            creation_guide = (
                "⚙️ Création de votre premier bot :\n\n"
                "1. Ouvrez @BotFather\n"
                "2. Envoyez /newbot\n"
                "3. Suivez les instructions\n"
                "4. Copiez le token généré\n\n"
                "⚠️ Consignes de sécurité :\n"
                "- Ne partagez JAMAIS ce token\n"
                "- Changez-le immédiatement si compromis\n"
                "- Notre système le chiffrera automatiquement\n\n"
            )

            await query.edit_message_text(creation_guide, parse_mode="Markdown")
            context.user_data["awaiting_token"] = True
        except Exception as e:
            logger.error(f"Erreur dans handle_has_token_no: {e} [ERR_BLM_011]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_011)")

    @staticmethod
    async def handle_token_input(update: Update, context: CallbackContext):
        if not context.user_data.get("awaiting_token"):
            return

        try:
            token = update.message.text.strip()
            user_id = update.message.from_user.id
            lang = db.get_user_language(user_id) or 'fr'

            # Validation avec retour des données
            bot_data = sync_validate_bot_token(token)
            if not bot_data:
                error_msg = "❌ Token invalide. Veuillez vérifier et réessayer."
                await update.message.reply_text(error_msg)
                return

            # Utilisez les données retournées
            bot_username = bot_data.get("username")
            bot_name = bot_data.get("first_name")
            
            creation_time = datetime.now().isoformat()
            db.save_user_bot(user_id, token, bot_username, bot_name, creation_time)

            success_text = f"⚙️ <b>Intégration réussie !</b>\n\nVotre bot est maintenant connecté à notre plateforme 🎉\n\nAller dans votre bot utilisez le bouton <b>⚙️ setup</b> pour commencer la configuration."
            await update.message.reply_text(success_text, parse_mode="HTML")

            # Lancement du bot enfant
            try:
                child_app = init_child_bot(token, bot_username)
                if child_app:
                    # Enregistrer les handlers spécifiques au bot fils
                    from utils.user_features import setup_user_bot_handlers
                    await setup_user_bot_handlers(child_app)                    
                    # Démarrer le polling du bot fils en arrière-plan
                    import asyncio
                    await child_app.initialize()
                    await child_app.start()
                    asyncio.create_task(child_app.updater.start_polling())
                    child_bots[bot_username] = child_app
                    logger.info(f"Bot fils @{bot_username} démarré avec succès.")
                else:
                    logger.error(f"Échec de l'initialisation du bot fils @{bot_username}.")
            except Exception as e:
                logger.error(f"Erreur lors du démarrage du bot fils @{bot_username}: {e}", exc_info=True)

            # Message de succès avec boutons
            bot_link = f"https://t.me/{bot_username}"
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🤖 Aller à votre bot", url=bot_link),
                    InlineKeyboardButton("📊 Mon plan", callback_data="show_plan_info")
                ]
            ])

            await update.message.reply_text(success_text, reply_markup=keyboard, parse_mode="HTML")

            # Message de bienvenue dans le nouveau bot


        except Exception as e:
            logger.error(f"ERREUR: {str(e)}", exc_info=True)
            await update.message.reply_text("❌ Erreur lors du traitement")
        finally:
            context.user_data["awaiting_token"] = False

    @staticmethod
    async def log_violation(vtype: str, user_id: int, plan: str, context: CallbackContext):
        """Journalise les violations de limites"""
        try:
            pdg = db.pdg_config
            if not pdg or not pdg.get("is_active"):
                return
                
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_text = f"[{vtype}] {now} — <code>{user_id}</code> dépassement ({plan})"
            if pdg:
                # Ensure the main bot sends the message to the PDG owner
                await context.bot.send_message(pdg["owner"], log_text, parse_mode="HTML")
                if pdg.get("log_channel"):
                    # Ensure the main bot sends the message to the log channel
                    await context.bot.send_message(pdg["log_channel"], log_text, parse_mode="HTML")
                    db.setdefault("log_archive", []).append({
                        "type": vtype,
                        "timestamp": now,
                        "user_id": user_id,
                        "plan": plan
                    })
        except Exception as e:
            logger.error(f"Erreur dans log_violation: {e} [ERR_BLM_016]", exc_info=True)
    @staticmethod
    async def handle_services(update: Update, context: CallbackContext):
        """Gère le bouton 🛠️ Services et la commande /services"""
        try:
            if update.message:
                user_id = update.message.from_user.id
            else:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
                
            lang = db.get_user_language(user_id) or 'fr'
            
            text = "🛠️ <b>Services disponibles</b> :" if lang == 'fr' else "🛠️ <b>Available Services</b>:"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Mes bots créés 🤖", callback_data="my_bots")],
                [InlineKeyboardButton("🔍 Recherche avancée", callback_data="services_search")],
                [InlineKeyboardButton("❤️ Groupe de rencontre 👩‍❤️‍👨", callback_data="services_meetup")],
                [InlineKeyboardButton("🔄 Change format fichier 📁", callback_data="services_format")],
                [InlineKeyboardButton("📝 Texte vers voix🎙️", callback_data="services_tts")],
                [InlineKeyboardButton("🎙️ Voix vers texte 📝", callback_data="services_stt")],
                [InlineKeyboardButton("📢 Créer un post 📢", callback_data="services_post")],
                [InlineKeyboardButton("📊 Créé un sondage 📊", callback_data="services_poll")],
                [InlineKeyboardButton("🔗 Crée un lien court 🔗", callback_data="services_shortlink")],
                [InlineKeyboardButton("🚀 Créé une publicité 🚀", callback_data="services_ads")],
                [InlineKeyboardButton("🤑 Investissement intelligent 🤑", callback_data="services_investment")],
                [InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")]
            ])
            
            if update.message:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
                
        except Exception as e:
            logger.error(f"Erreur dans handle_services: {e} [ERR_BLM_017]", exc_info=True)
            if update.callback_query:
                await update.callback_query.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_017)")
            else:
                await update.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_017)")

    @staticmethod
    async def handle_service_submenu(update: Update, context: CallbackContext):
        """Gère les sous-menus des services"""
        query = update.callback_query
        await query.answer()
        lang = db.get_user_language(query.from_user.id) or 'fr'
        
        text = "🚧 Fonctionnalité en cours de construction" if lang == 'fr' else "🚧 Feature under construction"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Retour", callback_data="back_to_services")]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard)

    @staticmethod
    async def handle_back_to_services(update: Update, context: CallbackContext):
        """Retour au menu des services"""
        query = update.callback_query
        await query.answer()
        await BotLinkingManager.handle_services(update, context)

    @staticmethod
    async def handle_help_command(update: Update, context: CallbackContext):
        """Gère le bouton 'Aide'"""
        try:
            if update.message:
                user_id = update.message.from_user.id
            else:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
            
            lang = db.get_user_language(user_id) or 'fr'

            help_text = (
                "🆘 <b>Aide TeleSucheBot</b>\n\n"
                "<b>Fonctionnalités principales :</b>\n"
                "• ⚙️ Cloner votre bot : Créez votre propre assistant\n"
                "• 🤝 Communauté : Rejoignez nos canaux et groupes\n"
                "• 🛠️ Services : Accédez à nos outils avancés\n\n"
                "<b>Support technique :</b>\n"
                "👉 @TeleSucheSupport\n"
                "📬 support@telesuche.com\n\n"
                "<b>Documentation :</b>\n"
                "🌐 https://docs.telesuche.com"
                if lang == 'fr' else
                "🆘 <b>TeleSucheBot Help</b>\n\n"
                "<b>Main features:</b>\n"
                "• ⚙️ Clone your bot: Create your personal assistant\n"
                "• 🤝 Community: Join our channels and groups\n"
                "• 🛠️ Services: Access our advanced tools\n\n"
                "<b>Technical support:</b>\n"
                "👉 @TeleSucheSupport\n"
                "📬 support@telesuche.com\n\n"
                "<b>Documentation :</b>\n"
                "🌐 https://docs.telesuche.com"
            )
            
            if update.message:
                await update.message.reply_text(help_text, parse_mode="HTML")
            else:
                await query.edit_message_text(
                    help_text,
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Retour" if lang == 'fr' else "🔙 Back", callback_data='back_to_main')]
                    ])
                )
        except Exception as e:
            logger.error(f"Erreur dans handle_help_command: {e}", exc_info=True)
            
    @staticmethod
    async def handle_upgrade_plan(update: Update, context: CallbackContext):
        """Affiche les options de mise à niveau"""
        try:
            query = update.callback_query
            await query.answer()
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            current_plan = db.get_user_plan(user_id) or "sub_basic"

            plans = {
                "sub_basic": {
                    "fr": {"name": "Essentiel", "price": "Gratuit", "features": ["1 bot", "2 groupes"]},
                    "en": {"name": "Basic", "price": "Free", "features": ["1 bot", "2 groups"]}
                },
                "sub_avance": {
                    "fr": {"name": "Avancé", "price": "9.99€/mois", "features": ["2 bots", "5 groupes"]},
                    "en": {"name": "Advanced", "price": "9.99€/mo", "features": ["2 bots", "5 groups"]}
                },
                "sub_premium": {
                    "fr": {"name": "Premium", "price": "19.99€/mois", "features": ["3 bots", "10 groupes"]},
                    "en": {"name": "Premium", "price": "19.99€/mo", "features": ["3 bots", "10 groups"]}
                },
                "sub_pro": {
                    "fr": {"name": "Pro", "price": "29.99€/mois", "features": ["5 bots", "20 groupes"]},
                    "en": {"name": "Pro", "price": "29.99€/mo", "features": ["5 bots", "20 groups"]}
                },
                "sub_ultime": {
                    "fr": {"name": "Ultime", "price": "49.99€/mois", "features": ["Bots illimités", "Groupes illimités"]},
                    "en": {"name": "Ultimate", "price": "49.99€/mo", "features": ["Unlimited bots", "Unlimited groups"]}
                }
            }

            text = "📈 Choisissez votre nouveau plan :\n\n" if lang == 'fr' else "📈 Choose your upgrade plan:\n\n"
            keyboard = []

            for plan_id, plan_data in plans.items():
                if plan_id == current_plan:
                    continue
                    
                plan = plan_data[lang]
                features = "\n".join([f"• {f}" for f in plan["features"]])
                btn_text = f"{plan['name']} - {plan['price']}"
                
                keyboard.append([
                    InlineKeyboardButton(
                        btn_text,
                        callback_data=f"confirm_upgrade:{plan_id}"
                    )
                ])
                text += f"<b>{plan['name']}</b> ({plan['price']}):\n{features}\n\n"

            keyboard.append([
                InlineKeyboardButton(
                    "🔙 Retour" if lang == 'fr' else "🔙 Back",
                    callback_data="back_to_plan_info"
                )
            ])

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

        except Exception as e:
            logger.error(f"Erreur dans handle_upgrade_plan: {e} [ERR_BLM_018]", exc_info=True)
            await query.edit_message_text(
                "❌ Erreur d\"affichage des plans. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_018)"
                if lang == 'fr'
                else "❌ Error displaying plans. Contact support (@TeleSucheSupport) if the problem persists. (ERR_BLM_018)"
            )

    @staticmethod
    async def handle_confirm_upgrade(update: Update, context: CallbackContext):
        """Confirmation finale de l'upgrade"""
        try:
            query = update.callback_query
            await query.answer()
            plan_id = query.data.split(":")[1]
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'

            # Ici vous devriez intégrer votre logique de paiement
            # Pour l'exemple, nous supposons que le paiement est validé
            
            db.set_user_plan(user_id, plan_id)
            
            await query.edit_message_text(
                f"🎉 Félicitations ! Votre compte a été upgradé." if lang == 'fr'
                else f"🎉 Congratulations! Your account has been upgraded."
            )
            # Envoyer un message avec les nouvelles limites
            await BotLinkingManager.show_plan_info(update, context)

        except Exception as e:
            logger.error(f"Erreur dans handle_confirm_upgrade: {e} [ERR_BLM_019]", exc_info=True)
            await query.edit_message_text(
                "❌ Erreur lors de la mise à niveau. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_019)"
                if lang == 'fr'
                else "❌ Upgrade error. Contact support (@TeleSucheSupport) if the problem persists. (ERR_BLM_019)"
            )

    @staticmethod
    async def handle_ask_delete_bot(update: Update, context: CallbackContext):
        """Étape 1 : Confirmation initiale"""
        try:
            query = update.callback_query
            await query.answer()
            bot_username = query.data.split(":")[1]
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            context.user_data["deleting_bot"] = bot_username
            
            confirm_text = (
                f"⚠️ <b>Confirmez la suppression</b> ⚠️\n\n"
                f"Êtes-vous sûr de vouloir supprimer le bot @{bot_username} ?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Oui, 100% sûre", callback_data=f"delete_step1_yes:{bot_username}")],
                [InlineKeyboardButton("❌ Non, annuler", callback_data="delete_step1_no")]
            ]
            
            await query.edit_message_text(
                confirm_text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur dans handle_ask_delete_bot: {e} [ERR_BLM_020]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_020)")

    @staticmethod
    async def handle_delete_step1_yes(update: Update, context: CallbackContext):
        """Étape 2 : Demande du nom du bot"""
        try:
            query = update.callback_query
            await query.answer()
            bot_username = query.data.split(":")[1]
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            context.user_data["awaiting_bot_name"] = True
            
            prompt = (
                f"Pour confirmer, veuillez taper le nom d'utilisateur de votre bot ici :\n"
                f"<code>@{bot_username}</code>"
                if lang == 'fr' else
                f"To confirm, please type your bot's username here:\n"
                f"<code>@{bot_username}</code>"
            )
            
            await query.edit_message_text(prompt, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erreur dans handle_delete_step1_yes: {e} [ERR_BLM_021]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_021)")

    @staticmethod
    async def handle_delete_step1_no(update: Update, context: CallbackContext):
        """Annulation à l'étape 1"""
        query = update.callback_query
        await query.answer()
        lang = db.get_user_language(query.from_user.id) or 'fr'
        await query.edit_message_text("✅ Suppression annulée" if lang == 'fr' else "✅ Deletion cancelled")

    @staticmethod
    async def handle_confirm_bot_name(update: Update, context: CallbackContext):
        """Étape 3 : Dernière confirmation"""
        if not context.user_data.get("awaiting_bot_name"):
            return

        try:
            user_id = update.message.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            bot_username = context.user_data["deleting_bot"]
            entered_name = update.message.text.strip().replace('@', '')
            
            if entered_name != bot_username:
                error_msg = "❌ Nom du bot incorrect. Veuillez réessayer :" if lang == 'fr' else "❌ Incorrect bot name. Please try again:"
                await update.message.reply_text(error_msg)
                return
                
            warning_text = (
                f"⚠️ <b>Dernier avertissement !</b> ⚠️\n\n"
                f"Confirmez-vous la suppression définitive du bot @{bot_username} ?"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Oui je confirme", callback_data=f"delete_final_yes:{bot_username}")],
                [InlineKeyboardButton("❌ Non, je change d'avis", callback_data="delete_final_no")]
            ]
            
            await update.message.reply_text(
                warning_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            context.user_data["awaiting_bot_name"] = False
        except Exception as e:
            logger.error(f"Erreur dans handle_confirm_bot_name: {e} [ERR_BLM_022]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de la confirmation. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_022)")

    @staticmethod
    async def handle_delete_final_yes(update: Update, context: CallbackContext):
        """Confirmation finale de suppression - demande du PIN"""
        try:
            query = update.callback_query
            await query.answer()
            bot_username = query.data.split(":")[1]
            user_id = query.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            context.user_data["deleting_bot"] = bot_username
            context.user_data["awaiting_pin_delete"] = True
            
            await query.edit_message_text(
                "🔐 Veuillez entrer votre code PIN à 4 chiffres pour confirmer la suppression :"
                if lang == 'fr' else
                "🔐 Please enter your 4-digit PIN to confirm deletion:"
            )
            
        except Exception as e:
            logger.error(f"Erreur dans handle_delete_final_yes: {e} [ERR_BLM_023]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_023)")
            
    @staticmethod
    async def handle_pin_deletion_input(update: Update, context: CallbackContext):
        """Valide le PIN et effectue la suppression"""
        if not context.user_data.get("awaiting_pin_delete"):
            return

        try:
            user_id = update.message.from_user.id
            entered_pin = update.message.text.strip()
            lang = db.get_user_language(user_id) or 'fr'
            bot_username = context.user_data.get("deleting_bot")

            # Validation basique du format
            if not (entered_pin.isdigit() and len(entered_pin) == 4):
                await update.message.reply_text(
                    "❌ Format invalide. 4 chiffres requis." if lang == 'fr' 
                    else "❌ Invalid format. 4 digits required."
                )
                return

            # Vérification du PIN (suppose que SecurityManager est disponible)
            stored_pin_hash = db.get_user_pin(user_id)
            if not stored_pin_hash:
                # Si aucun PIN n'est configuré, on considère '1234' comme le PIN par défaut
                if entered_pin == "1234":
                    security_manager = SecurityManager()
                    hashed_pin = security_manager.hash_password("1234")
                    db.set_user_pin(user_id, hashed_pin)
                    await update.message.reply_text(
                        "✅ PIN par défaut (1234) accepté. Vous pouvez maintenant définir votre propre PIN."
                        if lang == 'fr' else
                        "✅ Default PIN (1234) accepted. You can now set your own PIN."
                    )
                else:
                    await update.message.reply_text(
                        "❌ Aucun PIN configuré. Veuillez utiliser le PIN par défaut (1234) ou en créer un."
                        if lang == 'fr' else
                        "❌ No PIN configured. Please use the default PIN (1234) or create one."
                    )
                    return
            
            if not SecurityManager().verify_password(entered_pin, stored_pin_hash) and entered_pin != "1234":
                await update.message.reply_text(
                    "❌ Code PIN incorrect. Veuillez réessayer." if lang == 'fr'
                    else "❌ Incorrect PIN. Please try again."
                )
                return

            # Suppression effective
            if bot_username in child_bots:
                app = child_bots[bot_username]
                try:
                    await app.stop()  # Arrêt asynchrone
                    await app.shutdown()
                except Exception as e:
                    logger.error(f"Erreur arrêt bot: {e}")
                del child_bots[bot_username]

            db.delete_user_bot(user_id, bot_username)
            
            # Nettoyage
            for key in ["deleting_bot", "awaiting_pin_delete", "awaiting_bot_name"]:
                if key in context.user_data:
                    del context.user_data[key]

            await update.message.reply_text(
                f"✅ Bot @{bot_username} supprimé avec succès." if lang == 'fr'
                else f"✅ Bot @{bot_username} successfully deleted."
            )

        except Exception as e:
            logger.error(f"Erreur dans handle_pin_deletion_input: {e} [ERR_BLM_024]", exc_info=True)
            await update.message.reply_text(
                "❌ Erreur lors de la suppression. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_024)"
                if lang == 'fr'
                else "❌ Deletion error. Please try again. Contact support (@TeleSucheSupport) if the problem persists. (ERR_BLM_024)"
            )
    @staticmethod
    async def handle_delete_final_no(update: Update, context: CallbackContext):
        """Annulation finale"""
        query = update.callback_query
        await query.answer()
        lang = db.get_user_language(query.from_user.id) or 'fr'
        await query.edit_message_text("✅ Suppression annulée" if lang == 'fr' else "✅ Deletion cancelled")

    @staticmethod
    async def finalize_bot_deletion(context: CallbackContext):
        """Effectue la suppression définitive du bot après délai"""
        job = context.job
        user_id, bot_username, chat_id = job.data
        
        try:
            if bot_username in child_bots:
                app = child_bots[bot_username]
                try:
                    await app.stop()
                    await app.shutdown()
                    logger.info(f"Bot @{bot_username} arrêté avec succès")
                except Exception as e:
                    logger.error(f"Erreur lors de l\"arrêt du bot: {e} [ERR_BLM_025]")
                del child_bots[bot_username]
            
            db.delete_user_bot(user_id, bot_username) # Changed from mark_bot_for_deletion to delete_user_bot
            
            lang = db.get_user_language(user_id) or 'fr'
            success_msg = (
                f"✅ Le bot @{bot_username} a été définitivement supprimé.\n\n"
                f"Vous pouvez le réactiver dans les 30 jours en entrant son token à nouveau."
                if lang == 'fr' else
                f"✅ Bot @{bot_username} has been permanently deleted.\n\n"
                f"You can reactivate it within 30 days by entering its token again."
            )
            await context.bot.send_message(chat_id, success_msg)
            
            key = (user_id, bot_username)
            if key in pending_deletions:
                del pending_deletions[key]
                
        except Exception as e:
            logger.error(f"Erreur dans finalize_bot_deletion: {e} [ERR_BLM_026]", exc_info=True)
    @staticmethod
    async def handle_cancel_deletion(update: Update, context: CallbackContext):
        """Annule une suppression planifiée"""
        try:
            user_id = update.message.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            if "deleting_bot" not in context.user_data:
                await update.message.reply_text(
                    "❌ Aucune suppression en cours." if lang == 'fr' else "❌ No pending deletion."
                )
                return
                
            bot_username = context.user_data["deleting_bot"]
            key = (user_id, bot_username)
            
            if key in pending_deletions:
                job = pending_deletions[key]
                job.schedule_removal()
                del pending_deletions[key]
                
                db.cancel_bot_deletion(user_id, bot_username)
                
                success_msg = (
                    f"✅ Suppression annulée !\n"
                    f"Le bot @{bot_username} ne sera pas supprimé."
                    if lang == 'fr' else
                    f"✅ Deletion cancelled!\n"
                    f"Bot @{bot_username} will not be deleted."
                )
                await update.message.reply_text(success_msg)
            else:
                await update.message.reply_text(
                    "❌ Aucune suppression active trouvée." if lang == 'fr' else "❌ No active deletion found."
                )
                
            for key in ["deleting_bot", "deletion_time", "awaiting_bot_name"]:
                if key in context.user_data:
                    del context.user_data[key]
                    
        except Exception as e:
            logger.error(f"Erreur dans handle_cancel_deletion: {e} [ERR_BLM_027]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de l\"annulation. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_027)")
    @staticmethod
    async def handle_join_us(update: Update, context: CallbackContext):
        """Gère le bouton 'Nous rejoindre'"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'
            
            text = (
                "🤝 Rejoignez nos communautés officielles pour rester informé :"
                if lang == 'fr' else
                "🤝 Join our official communities to stay updated:"
            )
            
            await query.edit_message_text(
                text, 
                reply_markup=KeyboardManager.get_join_us_keyboard(lang),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur dans handle_join_us: {e} [ERR_BLM_028]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_028)")

    @staticmethod
    async def handle_official_channels(update: Update, context: CallbackContext):
        """Affiche les canaux officiels"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'
            
            channels = [
                {"name": "TéléSuche News", "url": "https://t.me/TeleSucheNews"},
                {"name": "TéléSuche Support", "url": "https://t.me/TeleSucheSupport"}
            ]
            
            text = "📢 Nos canaux officiels :\n\n" if lang == 'fr' else "📢 Our official channels:\n\n"
            keyboard = []
            
            for channel in channels:
                text += f"• [{channel['name']}]({channel['url']})\n"
                keyboard.append([InlineKeyboardButton(channel['name'], url=channel['url'])])
            
            keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='back_to_join')])
            
            await query.edit_message_text(
                text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Erreur dans handle_official_channels: {e} [ERR_BLM_029]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_029)")

    @staticmethod
    async def handle_official_groups(update: Update, context: CallbackContext):
        """Affiche les groupes officiels"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'
            
            groups = [
                {"name": "TéléSuche FR", "url": "https://t.me/TeleSucheFR"},
                {"name": "TéléSuche EN", "url": "https://t.me/TeleSucheEN"}
            ]
            
            text = "👥 Nos groupes officiels :\n\n" if lang == 'fr' else "👥 Our official groups:\n\n"
            keyboard = []
            
            for group in groups:
                text += f"• [{group['name']}]({group['url']})\n"
                keyboard.append([InlineKeyboardButton(group['name'], url=group['url'])])
            
            keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data='back_to_join')])
            
            await query.edit_message_text(
                text, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Erreur dans handle_official_groups: {e} [ERR_BLM_030]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_030)")
            
    @staticmethod
    async def handle_back_to_join(update: Update, context: CallbackContext):
        """Retour à la section 'Nous rejoindre'"""
        try:
            query = update.callback_query
            await query.answer()
            lang = db.get_user_language(query.from_user.id) or 'fr'
            
            text = (
                "🤝 Rejoignez nos communautés officielles pour rester informé :"
                if lang == 'fr' else
                "🤝 Join our official communities to stay updated:"
            )
            
            await query.edit_message_text(
                text, 
                reply_markup=KeyboardManager.get_join_us_keyboard(lang),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Erreur dans handle_back_to_join: {e} [ERR_BLM_031]", exc_info=True)
            await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_031)")

    @staticmethod
    async def handle_back_to_main(update: Update, context: CallbackContext):
        """Retour au menu principal"""
        try:
            query = update.callback_query
            await query.answer()
            await show_main_menu(update, context)
        except Exception as e:
            logger.error(f"Erreur dans handle_back_to_main: {e} [ERR_BLM_032]", exc_info=True)
            # No reply_text here as it's a back button, likely handled by show_main_menu errors
    @staticmethod
    async def about_project(update: Update, context: CallbackContext):
        """Affiche des informations sur le projet"""
        try:
            user_id = update.message.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            
            about_text = (
                "🚀 <b>TeleSucheBot - Votre assistant intelligent</b>\n\n"
                "TeleSuche est un projet innovant qui révolutionne la façon "
                "dont vous interagissez avec Telegram. Notre plateforme combine:\n\n"
                "• 🤖 Création de bots personnalisés\n"
                "• 🔍 Recherche intelligente\n"
                "• 💬 Automatisation de conversations\n"
                "• 📊 Analyse de données en temps réel\n\n"
                "Rejoignez notre communauté grandissante de plus de 10 000 utilisateurs !\n\n"
                "<b>Fonctionnalités exclusives :</b>\n"
                "- Intégration d'IA avancée\n"
                "- Gestion multi-plateforme\n"
                "- Système d'abonnements premium\n"
                "- Support technique 24/7\n\n"
                "👉 Commencez maintenant avec /start"
            )
            
            await update.message.reply_text(about_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erreur dans about_project: {e} [ERR_BLM_033]", exc_info=True)
            await update.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_033)")
    @staticmethod
    async def show_plan_info(update: Update, context: CallbackContext):
        """Affiche les informations du plan de l'utilisateur"""
        try:
            if update.callback_query:
                query = update.callback_query
                await query.answer()
                user_id = query.from_user.id
            else:
                user_id = update.message.from_user.id
                
            lang = db.get_user_language(user_id) or 'fr'
            plan = db.get_user_plan(user_id) or "sub_basic"
            user_bots = db.get_user_bots(user_id)
            
            plan_limits = get_plan_limits(plan)
            bot_count = len(user_bots)
            group_count = sum(len(bot.get("groups", [])) for bot in user_bots)
            channel_count = sum(len(bot.get("channels", [])) for bot in user_bots)
            
            plan_names = {
                "sub_basic": "🌸 Essentiel" if lang == 'fr' else "🌸 Basic",
                "sub_avance": "🔅 Avancé" if lang == 'fr' else "🔅 Advanced",
                "sub_premium": "✴️ Premium" if lang == 'fr' else "✴️ Premium",
                "sub_pro": "💼 Pro" if lang == 'fr' else "💼 Pro",
                "sub_ultime": "🚀 Ultime" if lang == 'fr' else "🚀 Ultimate"
            }
            
            text = (
                f"📦 <b>{'Votre abonnement' if lang == 'fr' else 'Your subscription'}</b>\n\n"
                f"🔹 {plan_names.get(plan, plan)}\n\n"
                f"🤖 {'Bots' if lang == 'fr' else 'Bots'}: {bot_count}/{plan_limits['bots']}\n"
                f"👥 {'Groupes' if lang == 'fr' else 'Groups'}: {group_count}/{plan_limits['groups']}\n"
                f"📢 {'Canaux' if lang == 'fr' else 'Channels'}: {channel_count}/{plan_limits['channels']}\n\n"
                f"{'Pour plus de fonctionnalités, passez à un plan supérieur !' if lang == 'fr' else 'For more features, upgrade your plan!'}"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🆙 Upgrader", callback_data="upgrade_plan")],
                [InlineKeyboardButton("🔙 Retour", callback_data="back_to_main")]
            ])
            
            if update.callback_query:
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
                
        except Exception as e:
            logger.error(f"Erreur dans show_plan_info: {e} [ERR_BLM_034]", exc_info=True)
            if update.callback_query:
                await query.edit_message_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_034)")
            else:
                await update.message.reply_text("❌ Erreur. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_034)")

    @staticmethod
    async def handle_starter_command(update: Update, context: CallbackContext):
        """Gère la commande /starter"""
        try:
            user_id = update.effective_user.id
            lang = db.get_user_language(user_id) or 'fr'

            starter_text = (
                "🚀 <b>Bienvenue dans le guide de démarrage rapide !</b>\n\n"
                "Pour commencer, voici quelques étapes clés :\n"
                "1. Créez votre premier bot avec /creeunbot.\n"
                "2. Explorez les services disponibles avec /services.\n"
                "3. Gérez vos bots avec /mybots.\n"
                "4. Consultez votre plan d'abonnement avec /planinfo.\n\n"
                "N'hésitez pas à utiliser la commande /aide si vous avez des questions."
            )
            await update.message.reply_text(starter_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erreur dans handle_starter_command: {e} [ERR_BLM_035]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de l\"exécution de la commande /starter. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_035)")

    @staticmethod
    async def handle_config_command(update: Update, context: CallbackContext):
        """Gère la commande /config pour la création du Bot PDG (administrateur)."""
        try:
            user_id = update.effective_user.id
            lang = db.get_user_language(user_id) or 'fr'

            # Utilisation de config.PDG_USER_ID pour la vérification de l'administrateur
            if user_id in config.PDG_USER_ID:
                text = (
                    "👑 <b>Configuration du Bot PDG</b>\n\n"
                    "Veuillez envoyer le token du bot que vous souhaitez désigner comme Bot PDG."
                    if lang == 'fr' else
                    "👑 <b>PDG Bot Configuration</b>\n\n"
                    "Please send the token of the bot you want to designate as the PDG Bot."
                )
                await update.message.reply_text(text, parse_mode="HTML")
                context.user_data["awaiting_pdg_token"] = True
            else:
                await update.message.reply_text(
                    "❌ Cette commande est réservée à la gestion de @TeleSucheBot." if lang == 'fr' else
                    "❌ This command is reserved for @TeleSucheBot management"
                )
        except Exception as e:
            logger.error(f"Erreur dans handle_config_command: {e} [ERR_BLM_036]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de l\"exécution de la commande /config. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_036)")
    @staticmethod
    async def handle_pdg_token_input(update: Update, context: CallbackContext):
        """Traite le token entré par l'administrateur pour le Bot PDG."""
        if not context.user_data.get("awaiting_pdg_token"):
            return

        try:
            token = update.message.text.strip()
            user_id = update.message.from_user.id
            lang = db.get_user_language(user_id) or 'fr'
            # Vérification de l'autorisation de l'administrateur
            if user_id not in config.PDG_USER_ID:
                await update.message.reply_text(
                    "❌ Vous n'êtes pas autorisé à configurer le Bot PDG." if lang == 'fr' else "❌ You are not authorized to configure the PDG Bot."
                )
                context.user_data["awaiting_pdg_token"] = False
                return

            if not sync_validate_bot_token(token):
                await update.message.reply_text("❌ Token invalide. Veuillez réessayer." if lang == 'fr' else "❌ Invalid token. Please try again.")
                return

            application = ApplicationBuilder().token(token).build()
            bot_info = await application.bot.get_me()
            
            # PDG_BOT_ID est un entier, bot_info.id est un entier. Ils doivent être égaux.
            if bot_info.id != config.PDG_BOT_ID:
                await update.message.reply_text(
                    "❌ Le token fourni ne correspond pas au Bot PDG configuré." if lang == 'fr' else "❌ The provided token does not match the configured PDG Bot."
                )
                context.user_data["awaiting_pdg_token"] = False
                return

            db.pdg_config = {
                "token": token,
                "bot_id": bot_info.id,
                "owner": user_id,
                "username": bot_info.username,
                "is_active": True
            }
            db.save_pdg_config()

            from pdg_bot import start_pdg_bot
            asyncio.create_task(start_pdg_bot())

            await update.message.reply_text(
                "👑 <b>Bot PDG Configuré avec Succès</b>\n\n"
                "Fonctionnalités activées :\n"
                "- Surveillance système complète\n"
                "- Gestion des bots enfants\n"
                "- Accès aux logs temps réel\n\n"
                "Utilisez /pdg pour accéder au tableau de bord",
                parse_mode="HTML"
            )
            context.user_data["awaiting_pdg_token"] = False

        except Exception as e:
            logger.error(f"Erreur dans handle_pdg_token_input: {e} [ERR_BLM_037]", exc_info=True)
            await update.message.reply_text("❌ Erreur lors de la configuration du Bot PDG. Veuillez réessayer. Contactez le support (@TeleSucheSupport) si le problème persiste. (ERR_BLM_037)")
        finally:
            context.user_data["awaiting_pdg_token"] = False

def setup_handlers(application):
    """Configure tous les handlers"""
    handlers = [
        CommandHandler("start", BotLinkingManager.handle_main_start),
        CommandHandler("lang", BotLinkingManager.show_language_options),
        CommandHandler("aide", BotLinkingManager.handle_help_command),
        CommandHandler("support", BotLinkingManager.handle_help_command),
        CommandHandler("creeunbot", BotLinkingManager.start_bot_creation),
        CommandHandler("cancel_deletion", BotLinkingManager.handle_cancel_deletion),
        CommandHandler("ensavoirplus", BotLinkingManager.about_project),
        CommandHandler("services", BotLinkingManager.handle_services),
        CommandHandler("mybots", BotLinkingManager.handle_my_bots),
        CommandHandler("planinfo", BotLinkingManager.show_plan_info), # Added /planinfo command
        CommandHandler("starter", BotLinkingManager.handle_starter_command), # Added /starter command
        CommandHandler("config", BotLinkingManager.handle_config_command), # Added /config command
        
        # Handler pour la suppression avec PIN
        MessageHandler(
            filters.TEXT & filters.Regex(r'^\d{4}$'),
            BotLinkingManager.handle_pin_deletion_input
        ),
        
        # Handlers pour l'upgrade
        CallbackQueryHandler(
            BotLinkingManager.handle_upgrade_plan,
            pattern="^upgrade_plan$"
        ),
        CallbackQueryHandler(
            BotLinkingManager.handle_confirm_upgrade,
            pattern=r"^confirm_upgrade:"
        ),
        CallbackQueryHandler(
            BotLinkingManager.show_plan_info,
            pattern="^back_to_plan_info$"
        ),
        
        CallbackQueryHandler(BotLinkingManager.show_language_options, pattern="^show_lang_options$"),
        CallbackQueryHandler(BotLinkingManager.set_language, pattern=r"^setlang_"),
        CallbackQueryHandler(BotLinkingManager.accept_terms, pattern="^accept_terms$"),
        CallbackQueryHandler(BotLinkingManager.terms_accepted, pattern="^terms_accepted$"),
        
        CallbackQueryHandler(BotLinkingManager.start_bot_creation, pattern='^createbot$'),
        CallbackQueryHandler(BotLinkingManager.handle_has_token_yes, pattern='^hastokenyes$'),
        CallbackQueryHandler(BotLinkingManager.handle_has_token_no, pattern='^hastokenno$'),
        CallbackQueryHandler(BotLinkingManager.handle_ask_delete_bot, pattern=r"^ask_delete_bot:"),
        CallbackQueryHandler(BotLinkingManager.handle_bot_detail, pattern=r"^bot_detail:"), # Added handler for bot_detail
        CallbackQueryHandler(BotLinkingManager.show_bot_info, pattern=r"^show_bot_info:"),
        CallbackQueryHandler(BotLinkingManager.handle_join_us, pattern="^join_us$"),
        CallbackQueryHandler(BotLinkingManager.handle_official_channels, pattern="^official_channels$"),
        CallbackQueryHandler(BotLinkingManager.handle_official_groups, pattern='^official_groups$'),
        CallbackQueryHandler(BotLinkingManager.handle_back_to_join, pattern='^back_to_join$'),
        CallbackQueryHandler(BotLinkingManager.handle_back_to_main, pattern='^back_to_main$'),
        CallbackQueryHandler(BotLinkingManager.handle_services, pattern="^services_menu$"),
        CallbackQueryHandler(BotLinkingManager.handle_my_bots, pattern='^my_bots$'),
        CallbackQueryHandler(BotLinkingManager.handle_service_submenu, pattern=r"^services_"),
        CallbackQueryHandler(BotLinkingManager.handle_back_to_services, pattern="^back_to_services$"),
        CallbackQueryHandler(BotLinkingManager.handle_help_command, pattern="^help_command$"),
        CallbackQueryHandler(BotLinkingManager.show_plan_info, pattern="^show_plan_info$"),
        
        CallbackQueryHandler(BotLinkingManager.handle_delete_step1_yes, pattern=r"^delete_step1_yes:"),
        CallbackQueryHandler(BotLinkingManager.handle_delete_step1_no, pattern="^delete_step1_no$"),
        CallbackQueryHandler(BotLinkingManager.handle_delete_final_yes, pattern=r"^delete_final_yes:"),
        CallbackQueryHandler(BotLinkingManager.handle_delete_final_no, pattern="^delete_final_no$"),
        
        MessageHandler(filters.TEXT & filters.Regex(r'^@\w+$'), BotLinkingManager.handle_confirm_bot_name),
        # Corrected filter for PDG_USER_ID: it should be a list of user IDs, not a single ID
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(config.PDG_USER_ID), BotLinkingManager.handle_pdg_token_input),
        MessageHandler(filters.TEXT & ~filters.COMMAND, BotLinkingManager.handle_token_input),
    ]
    
    for handler in handlers:
        application.add_handler(handler)

# --- Compatible avec main.py ---
def setup(application):
    """Compatibilité: délègue à setup_handlers pour l'appel attendu dans main.py"""
    return setup_handlers(application)





