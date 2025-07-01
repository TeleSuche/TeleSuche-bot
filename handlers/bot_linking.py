import logging
logger = logging.getLogger(__name__)
# telegram_gemini_5/handlers/bot_linking.py

"""
Gestion de liaison de bots enfants et bot PDG.
Inclut : validation, création, quotas d’abonnement, log, suppression en 4 étapes.
"""
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CallbackContext, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters
)
from typing import Dict, Tuple
from utils.memory_full import db
from utils.api_client import validate_bot_token
from utils.user_features import get_welcome_message
from utils.user_administrator import setup_user_bot_handlers
from extensions.handlers.subscriptions import (
    check_bot_limits, check_group_limits, get_plan_limits
)
from pdg_bot import init_pdg_bot  # Import du gestionnaire PDG

logger = logging.getLogger(__name__)
PDG_BOT_ID = 999999999  # ID spécial du bot PDG
child_bots: Dict[str, Tuple['TeleBot', threading.Thread]] = {}

class BotLinkingManager:

    @staticmethod
    def get_bot_creation_keyboard(lang: str = 'fr') -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Oui" if lang == 'fr' else "✅ Yes", callback_data='hastoken_yes'),
                InlineKeyboardButton("➕ Non" if lang == 'fr' else "➕ No", callback_data='hastoken_no')
            ]
        ])

    @staticmethod
    async def start_bot_creation(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        lang = db.get_user_language(query.from_user.id)
        msg = "⚙️ Cloner votre bot"
        await query.edit_message_text(msg, reply_markup=BotLinkingManager.get_bot_creation_keyboard(lang))

    @staticmethod
    async def handle_token_input(update: Update, context: CallbackContext):
        if not context.user_data.get("awaiting_token"):
            return

        token = update.message.text.strip()
        user_id = update.message.from_user.id
        lang = db.get_user_language(user_id)
        plan = db.get("user_plans", {}).get(user_id, "sub_basic")

        if not validate_bot_token(token):
            return await update.message.reply_text("❌ Token invalide. Veuillez réessayer :")

        from telebot import TeleBot
        bot_instance = TeleBot(token, parse_mode="HTML")
        bot_instance.remove_webhook()
        bot_info = bot_instance.get_me()
        bot_username = bot_info.username
        bot_name = bot_info.first_name
        bot_link = f"https://t.me/{bot_username}"

        # Gestion spéciale pour le bot PDG
        if bot_info.id == PDG_BOT_ID:
            db["pdg_bot"] = {
                "token": token, 
                "bot_id": bot_info.id, 
                "owner": user_id,
                "username": bot_username,
                "is_active": True
            }
            
            # Message de confirmation PDG
            await update.message.reply_text(
                "👑 <b>Bot PDG Configuré avec Succès</b>\n\n"
                "Fonctionnalités activées :\n"
                "- Surveillance système complète\n"
                "- Gestion des bots enfants\n"
                "- Accès aux logs temps réel\n\n"
                "Utilisez /pdg pour accéder au tableau de bord",
                parse_mode="HTML"
            )
            
            # Démarrer le bot PDG dans un processus séparé
            init_pdg_bot()
            return

        # Vérification des quotas pour les bots enfants
        if not await check_bot_limits(user_id):
            await update.message.reply_text("🚫 Limite de bots atteinte.")
            await BotLinkingManager.log_violation("BOT", user_id, plan, context)
            return

        if not await check_group_limits(user_id, new_group_id=0):
            await update.message.reply_text("🚫 Limite de groupes atteinte.")
            await BotLinkingManager.log_violation("GROUPE", user_id, plan, context)
            return

        user_bots = db.get_user_bots(user_id)
        total_channels = sum(len(b.get("channels", [])) for b in user_bots)
        if total_channels >= get_plan_limits(plan)["channels"]:
            await update.message.reply_text("🚫 Limite de canaux atteinte.")
            await BotLinkingManager.log_violation("CANAL", user_id, plan, context)
            return

        # Gestion des bots existants
        if bot_username in child_bots:
            try:
                old_bot, old_thread = child_bots[bot_username]
                old_bot.stop_polling()
            except Exception as e:
                logger.error(f"Erreur arrêt ancien bot: {e}")

        # Enregistrement du nouveau bot
        db.save_user_bot(user_id, token, bot_username, bot_name)
        if user_id not in db.get("user_plans", {}):
            db.setdefault("user_plans", {})[user_id] = "sub_basic"

        # Configuration et démarrage
        setup_user_bot_handlers(bot_instance)
        thread = threading.Thread(
            target=bot_instance.polling, kwargs={"non_stop": True}, daemon=True
        )
        thread.start()
        child_bots[bot_username] = (bot_instance, thread)

        # Message de succès
        success_text = (
            f"⚙️ <b>Intégration réussie !</b>\n\n"
            f"Votre bot est maintenant connecté à notre plateforme 🎉\n"
            f"Utilisez /setup dans votre bot pour commencer."
        )

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Aller à votre bot", url=bot_link)],
            [InlineKeyboardButton("🆙 Passer à un plan supérieur", callback_data="upgrade_plan")]
        ])
        await update.message.reply_text(success_text, reply_markup=buttons, parse_mode="HTML")

        # Message de bienvenue
        try:
            welcome_msg = get_welcome_message(lang, bot_name=bot_username)
            setup_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Setup", callback_data="trigger_setup")]
            ])
            bot_instance.send_message(user_id, welcome_msg, parse_mode="HTML", reply_markup=setup_btn)
        except Exception as e:
            logger.warning(f"Erreur message de bienvenue : {e}")

        context.user_data["awaiting_token"] = False

    @staticmethod
    async def log_violation(vtype: str, user_id: int, plan: str, context: CallbackContext):
        pdg = db.get("pdg_bot")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_text = f"[{vtype}] {now} — <code>{user_id}</code> dépassement ({plan})"
        if pdg:
            await context.bot.send_message(pdg["owner"], log_text, parse_mode="HTML")
            if pdg.get("log_channel"):
                await context.bot.send_message(pdg["log_channel"], log_text, parse_mode="HTML")
                db.setdefault("log_archive", []).append({
                    "type": vtype,
                    "timestamp": now,
                    "user_id": user_id,
                    "plan": plan
                })

    @staticmethod
    async def confirm_bot_deletion(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        bot_username = query.data.split(":")[1]
        context.user_data["deletion_bot"] = bot_username
        context.user_data["deletion_stage"] = 1
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛑 Je confirme la suppression", callback_data="confirm_deletion_step1")]
        ])
        await query.edit_message_text(f"⚠️ Suppression du bot @{bot_username}.\nÉtape 1/4 : Veux-tu vraiment supprimer ce bot ?", reply_markup=keyboard)

    @staticmethod
    async def handle_deletion_steps(update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        stage = context.user_data.get("deletion_stage")
        bot_username = context.user_data.get("deletion_bot")

        if stage == 1:
            context.user_data["deletion_stage"] = 2
            await query.edit_message_text(f"✍️ Étape 2/4 : Tape exactement le nom du bot @{bot_username} pour confirmer.")
        elif stage == 3:
            context.user_data["deletion_stage"] = 4
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Je valide maintenant", callback_data="confirm_deletion_step4")]
            ])
            await query.edit_message_text("🧨 Étape 4/4 : Prêt à supprimer ? Confirme la suppression finale.", reply_markup=keyboard)
        elif stage == 4:
            await BotLinkingManager.perform_deletion(update, context, bot_username)

    @staticmethod
    async def handle_deletion_text(update: Update, context: CallbackContext):
        if context.user_data.get("deletion_stage") == 2:
            typed = update.message.text.strip().lstrip("@").lower()
            expected = context.user_data["deletion_bot"].lower()
            if typed == expected:
                context.user_data["deletion_stage"] = 3
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 Je reconfirme", callback_data="confirm_deletion_step3")]
                ])
                await update.message.reply_text("✅ Étape 3/4 : Nom validé. Confirme à nouveau pour passer à l'étape finale.", reply_markup=keyboard)
            else:
                await update.message.reply_text("❌ Nom incorrect. Veuillez taper exactement le nom du bot.")

    @staticmethod
    async def perform_deletion(update: Update, context: CallbackContext, bot_username: str):
        user_id = update.effective_user.id
        context.user_data.pop("deletion_stage", None)
        context.user_data.pop("deletion_bot", None)
        await update.callback_query.edit_message_text("🕒 Suppression programmée. Le bot sera supprimé dans 60 minutes.")

        async def delayed_deletion(ctx: CallbackContext):
            db.delete_user_bot(user_id, bot_username)
            try:
                child_bots.pop(bot_username)[0].stop_polling()
            except:
                pass
            await ctx.bot.send_message(user_id, f"🗑 Bot @{bot_username} supprimé avec succès.")

        context.job_queue.run_once(delayed_deletion, when=60 * 60, name=f"delete_{bot_username}")

    @staticmethod
    async def handle_my_bots(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        lang = db.get_user_language(user_id)
        bots = db.get_user_bots(user_id)
        if not bots:
            return await update.message.reply_text("🤖 Aucun bot connecté.")
        text = "🤖 Vos bots connectés :"
        keyboard = [
            [
                InlineKeyboardButton("ℹ️ Info", callback_data=f"bot_info:{b['bot_username']}"),
                InlineKeyboardButton("🗑 Supprimer", callback_data=f"ask_delete_bot:{b['bot_username']}")
            ] for b in bots
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    @staticmethod
    def setup_handlers(application: Application):
        application.add_handler(CallbackQueryHandler(BotLinkingManager.start_bot_creation, pattern='^create_bot$'))
        application.add_handler(CallbackQueryHandler(BotLinkingManager.handle_my_bots, pattern='^mybots$'))
        application.add_handler(CommandHandler("mybots", BotLinkingManager.handle_my_bots))
        application.add_handler(CallbackQueryHandler(BotLinkingManager.confirm_bot_deletion, pattern=r"^ask_delete_bot:"))
        application.add_handler(CallbackQueryHandler(BotLinkingManager.handle_deletion_steps, pattern=r"^confirm_deletion_step[134]$"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, BotLinkingManager.handle_deletion_text))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, BotLinkingManager.handle_token_input))

# Initialisation
bot_linking_manager = BotLinkingManager()