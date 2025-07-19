# classes.py
import logging
import os
import json
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.database import DatabaseManager
from utils.security import SecurityManager
from utils.translations import get_text as t

logger = logging.getLogger(__name__)

class AdminHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats")],
            [InlineKeyboardButton("📜 Logs système", callback_data="admin_logs")],
            [InlineKeyboardButton("🛠️ Maintenance", callback_data="admin_maintenance")],
            [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
        ])
        
        await update.message.reply_text(
            text=t(lang, "admin_panel_welcome"),
            reply_markup=keyboard
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_count = self.db_manager.get_user_count()
        active_users = self.db_manager.get_active_user_count()
        lang = self.db_manager.get_user_language(update.effective_user.id) or 'fr'
        
        await update.message.reply_text(
            t(lang, "stats_message").format(
                user_count=user_count,
                active_users=active_users
            )
        )

    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            with open("bot.log", "rb") as log_file:
                await update.message.reply_document(
                    document=log_file,
                    caption="📜 Logs système"
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur lors de la récupération des logs: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data == "admin_stats":
            await self.stats_command(update, context)
        elif data == "admin_logs":
            await self.logs_command(update, context)
        await query.answer()

class ModerationHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager, security_manager: SecurityManager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager
        self.security_manager = security_manager

    async def kick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "kick_usage"))
            return
        
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or t(lang, "no_reason")
        
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_id
            )
            await context.bot.unban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_id
            )
            await update.message.reply_text(
                t(lang, "kick_success").format(
                    user_id=target_id,
                    reason=reason
                )
            )
        except Exception as e:
            await update.message.reply_text(t(lang, "kick_error").format(error=str(e)))

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "ban_usage"))
            return
        
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or t(lang, "no_reason")
        
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_id
            )
            await update.message.reply_text(
                t(lang, "ban_success").format(
                    user_id=target_id,
                    reason=reason
                )
            )
        except Exception as e:
            await update.message.reply_text(t(lang, "ban_error").format(error=str(e)))

    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "mute_usage"))
            return
        
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or t(lang, "no_reason")
        
        try:
            # Implémentation réelle dépendante de l'API Telegram
            await update.message.reply_text(
                t(lang, "mute_success").format(
                    user_id=target_id,
                    reason=reason
                )
            )
        except Exception as e:
            await update.message.reply_text(t(lang, "mute_error").format(error=str(e)))

    async def unmute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "unmute_usage"))
            return
        
        target_id = int(context.args[0])
        
        try:
            # Implémentation réelle dépendante de l'API Telegram
            await update.message.reply_text(
                t(lang, "unmute_success").format(user_id=target_id)
            )
        except Exception as e:
            await update.message.reply_text(t(lang, "unmute_error").format(error=str(e)))

    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "warn_usage"))
            return
        
        target_id = int(context.args[0])
        reason = " ".join(context.args[1:]) or t(lang, "no_reason")
        
        try:
            warn_count = self.db_manager.increment_warn_count(target_id)
            max_warns = 3
            
            await update.message.reply_text(
                t(lang, "warn_success").format(
                    user_id=target_id,
                    reason=reason,
                    count=warn_count,
                    max=max_warns
                )
            )
            
            if warn_count >= max_warns:
                await self.kick_command(update, context)
        except Exception as e:
            await update.message.reply_text(t(lang, "warn_error").format(error=str(e)))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Gestion des callbacks de modération
        pass

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Analyse des messages pour modération
        pass

class ShopHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager

    async def shop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        credits = self.db_manager.get_user_credits(user_id)
        
        products = [
            {"id": 1, "name": "100 crédits", "price": 5.00},
            {"id": 2, "name": "500 crédits", "price": 20.00},
            {"id": 3, "name": "2000 crédits", "price": 75.00}
        ]
        
        message = t(lang, "shop_welcome").format(credits=credits) + "\n\n"
        message += t(lang, "available_products") + ":\n"
        
        for product in products:
            message += f"- {product['name']}: ${product['price']:.2f}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "buy_button"), callback_data="shop_buy")],
            [InlineKeyboardButton(t(lang, "credits_button"), callback_data="shop_credits")]
        ])
        
        await update.message.reply_text(message, reply_markup=keyboard)

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "buy_usage"))
            return
        
        product_id = int(context.args[0])
        # Logique d'achat réelle ici
        
        await update.message.reply_text(t(lang, "purchase_success"))

    async def credits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        credits = self.db_manager.get_user_credits(user_id)
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        await update.message.reply_text(t(lang, "credits_balance").format(credits=credits))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data == "shop_buy":
            await self.buy_command(update, context)
        elif data == "shop_credits":
            await self.credits_command(update, context)
        
        await query.answer()

class SubscriptionHandler:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        subscriptions = [
            {"id": 1, "name": "Basic", "price": 5.00, "features": ["Recherche illimitée", "5 groupes"]},
            {"id": 2, "name": "Premium", "price": 15.00, "features": ["Recherche illimitée", "Groupes illimités", "Support prioritaire"]},
            {"id": 3, "name": "Enterprise", "price": 50.00, "features": ["Tout dans Premium", "Comptes multiples", "API d'intégration"]}
        ]
        
        message = t(lang, "subscription_options") + ":\n\n"
        
        for sub in subscriptions:
            message += f"<b>{sub['name']}</b> - ${sub['price']:.2f}/mois\n"
            message += "• " + "\n• ".join(sub['features']) + "\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"S'abonner à {sub['name']}", callback_data=f"sub_{sub['id']}")] 
            for sub in subscriptions
        ])
        
        await update.message.reply_text(message, parse_mode="HTML", reply_markup=keyboard)

    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.subscribe_command(update, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data.startswith("sub_"):
            sub_id = int(data.replace("sub_", ""))
            # Traitement de l'abonnement
            await query.answer(f"Abonnement #{sub_id} sélectionné")

class ReferralHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager

    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        referrals = self.db_manager.get_user_referrals(user_id)
        
        message = t(lang, "referral_info").format(
            count=len(referrals),
            bonus=5  # Bonus par filleul
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "generate_link"), callback_data="ref_generate")],
            [InlineKeyboardButton(t(lang, "view_referrals"), callback_data="ref_list")]
        ])
        
        await update.message.reply_text(message, reply_markup=keyboard)

    async def invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        ref_code = self.db_manager.get_referral_code(user_id)
        bot_username = (await context.bot.get_me()).username
        
        invite_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
        
        await update.message.reply_text(
            t(lang, "invite_link_message").format(link=invite_link)
        )

    async def filleuls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        referrals = self.db_manager.get_user_referrals(user_id)
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not referrals:
            await update.message.reply_text(t(lang, "no_referrals"))
            return
        
        message = t(lang, "referral_list_header") + ":\n\n"
        for i, ref in enumerate(referrals, 1):
            message += f"{i}. {ref['username']} - {ref['join_date']}\n"
        
        await update.message.reply_text(message)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data == "ref_generate":
            await self.invite_command(update, context)
        elif data == "ref_list":
            await self.filleuls_command(update, context)
        
        await query.answer()

class SearchHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        if not context.args:
            await update.message.reply_text(t(lang, "search_usage"))
            return
        
        query = " ".join(context.args)
        results = self.db_manager.search_content(query)
        
        if not results:
            await update.message.reply_text(t(lang, "no_results"))
            return
        
        message = t(lang, "search_results_header") + ":\n\n"
        for i, result in enumerate(results[:5], 1):
            message += f"{i}. {result['title']}\n   {result['snippet']}\n\n"
        
        await update.message.reply_text(message)

    async def index_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        lang = self.db_manager.get_user_language(user_id) or 'fr'
        
        await update.message.reply_text(t(lang, "index_instructions"))

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Traitement des documents pour indexation
        pass

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Gestion des callbacks de recherche
        pass

class UserHandler:
    def __init__(self, db_manager: DatabaseManager, translation_manager):
        self.db_manager = db_manager
        self.translation_manager = translation_manager

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = self.db_manager.get_user_data(user_id)
        lang = user_data.get('language', 'fr')
        
        profile_text = t(lang, "profile_template").format(
            username=update.effective_user.full_name,
            user_id=user_id,
            join_date=user_data.get('join_date', 'N/A'),
            credits=user_data.get('credits', 0),
            status=user_data.get('status', 'Basic'),
            referrals=len(user_data.get('referrals', []))
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(t(lang, "edit_profile"), callback_data="profile_edit")]
        ])
        
        await update.message.reply_text(profile_text, reply_markup=keyboard)

    async def me_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = self.db_manager.get_user_data(user.id)
        
        await update.message.reply_text(
            f"👤 ID: {user.id}\n"
            f"📛 Nom: {user.full_name}\n"
            f"🌐 Langue: {user_data.get('language', 'fr')}\n"
            f"💳 Crédits: {user_data.get('credits', 0)}\n"
            f"⭐ Statut: {user_data.get('status', 'Basic')}"
        )

    def get_all_admin_bot_tokens(self) -> List[str]:
        try:
            path = "/storage/emulated/0/telegram_bot/admin_tokens.json"
            # Créer le répertoire s'il n'existe pas
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                # Écrire un fichier par défaut
                default_data = {"admin_bots": []}
                with open(path, "w") as file:
                    json.dump(default_data, file)
                logger.info("Fichier admin_tokens.json créé par défaut.")
                return []

            with open(path, "r") as file:
                data = json.load(file)
                return [bot["token"] for bot in data.get("admin_bots", [])]
        except Exception as e:
            logger.error(f"Erreur de lecture des tokens : {e}")
            return []

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer("Fonctionnalité en développement")