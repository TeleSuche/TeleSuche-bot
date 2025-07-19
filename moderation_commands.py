from datetime import datetime
"""
Gestionnaire des fonctions de modération
"""

import logging
import re
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest, Forbidden

class ModerationHandler:
    """Gestionnaire des commandes de modération"""
    
    def __init__(self, db, security):
        self.db = db
        self.security = security
        self.logger = logging.getLogger(__name__)
    
    async def kick_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /kick - Expulser un utilisateur"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user['user_id'],
                until_date=datetime.now() + timedelta(seconds=30)
            )

            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='kick',
                reason=" ".join(context.args[1:]) if context.args and len(context.args) > 1 else None
            )
            
            username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
            await update.message.reply_text(f"✅ {username} a été expulsé du groupe.")
            
        except BadRequest as e:
            self.logger.error(f"Erreur lors de l'expulsion: {e}")
            await update.message.reply_text("❌ Impossible d'expulser l'utilisateur.")
        except Forbidden as e:
            self.logger.error(f"Permission denied: {e}")
            await update.message.reply_text("❌ Permissions insuffisantes pour expulser.")

    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /ban - Bannir un utilisateur"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        ban_duration = None
        reason = None
        
        if context.args and len(context.args) > 1:
            try:
                duration_str = context.args[1]
                if duration_str.endswith('h'):
                    hours = int(duration_str[:-1])
                    ban_duration = datetime.now() + timedelta(hours=hours)
                    reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
                elif duration_str.endswith('d'):
                    days = int(duration_str[:-1])
                    ban_duration = datetime.now() + timedelta(days=days)
                    reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
                else:
                    reason = " ".join(context.args[1:])
            except (ValueError, IndexError):
                reason = " ".join(context.args[1:])
        
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user['user_id'],
                until_date=ban_duration
            )
            
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='ban',
                reason=reason,
                duration=ban_duration
            )
            
            duration_text = ""
            if ban_duration:
                if context.args and len(context.args) > 1:
                    duration_text = f" pour {context.args[1]}"
                else:
                    duration_text = " temporairement"
            else:
                duration_text = " définitivement"
            
            username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
            await update.message.reply_text(f"🔨 {username} a été banni{duration_text}.")
            
        except BadRequest as e:
            self.logger.error(f"Erreur lors du bannissement: {e}")
            await update.message.reply_text("❌ Impossible de bannir l'utilisateur.")
        except Forbidden as e:
            self.logger.error(f"Permission denied: {e}")
            await update.message.reply_text("❌ Permissions insuffisantes pour bannir.")

    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /mute - Réduire au silence"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        mute_duration = datetime.now() + timedelta(hours=1)
        reason = None
        
        if context.args and len(context.args) > 1:
            try:
                duration_str = context.args[1]
                if duration_str.endswith('m'):
                    minutes = int(duration_str[:-1])
                    mute_duration = datetime.now() + timedelta(minutes=minutes)
                    reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
                elif duration_str.endswith('h'):
                    hours = int(duration_str[:-1])
                    mute_duration = datetime.now() + timedelta(hours=hours)
                    reason = " ".join(context.args[2:]) if len(context.args) > 2 else None
                else:
                    reason = " ".join(context.args[1:])
            except (ValueError, IndexError):
                reason = " ".join(context.args[1:])
        
        try:
            permissions = {
                'can_send_messages': False,
                'can_send_media_messages': False,
                'can_send_other_messages': False,
                'can_add_web_page_previews': False
            }
            
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user['user_id'],
                permissions=permissions,
                until_date=mute_duration
            )
            
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='mute',
                reason=reason,
                duration=mute_duration
            )
            
            username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
            await update.message.reply_text(
                f"🔇 {username} a été réduit au silence jusqu'à {mute_duration.strftime('%Y-%m-%d %H:%M')}."
            )
            
        except BadRequest as e:
            self.logger.error(f"Erreur lors du mute: {e}")
            await update.message.reply_text("❌ Impossible de réduire au silence.")
        except Forbidden as e:
            self.logger.error(f"Permission denied: {e}")
            await update.message.reply_text("❌ Permissions insuffisantes pour réduire au silence.")

    async def unmute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /unmute - Retirer le silence"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        try:
            permissions = {
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
            
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user['user_id'],
                permissions=permissions
            )
            
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='unmute'
            )
            
            username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
            await update.message.reply_text(f"🔊 {username} peut de nouveau parler.")
            
        except BadRequest as e:
            self.logger.error(f"Erreur lors de l'unmute: {e}")
            await update.message.reply_text("❌ Impossible de retirer le silence.")
        except Forbidden as e:
            self.logger.error(f"Permission denied: {e}")
            await update.message.reply_text("❌ Permissions insuffisantes pour retirer le silence.")

    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /warn - Avertir un utilisateur"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        reason = " ".join(context.args[1:]) if context.args and len(context.args) > 1 else "Aucune raison spécifiée"
        
        warning_count = self.db.add_warning(
            chat_id=update.effective_chat.id,
            user_id=target_user['user_id'],
            admin_id=update.effective_user.id,
            reason=reason
        )
        
        max_warnings = self.db.get_group_setting(update.effective_chat.id, 'max_warnings', 3)
        
        if warning_count >= max_warnings:
            try:
                await context.bot.ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=target_user['user_id']
                )
                
                username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
                await update.message.reply_text(
                    f"⚠️ {username} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                    f"Raison: {reason}\n\n"
                    f"🔨 Utilisateur banni automatiquement (limite d'avertissements atteinte)."
                )
            except (BadRequest, Forbidden) as e:
                self.logger.error(f"Erreur lors du ban automatique: {e}")
                username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
                await update.message.reply_text(
                    f"⚠️ {username} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                    f"Raison: {reason}\n\n"
                    f"❌ Impossible de bannir automatiquement."
                )
        else:
            username = target_user.get('username', target_user.get('first_name', 'Utilisateur'))
            await update.message.reply_text(
                f"⚠️ {username} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                f"Raison: {reason}"
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les messages pour la modération automatique"""
        if not update.message or not update.message.text:
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_text = update.message.text.lower()
        
        banned_words = self.db.get_group_setting(chat_id, 'banned_words', [])
        for word in banned_words:
            if word.lower() in message_text:
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Message supprimé: contenu interdit détecté.",
                        reply_to_message_id=None
                    )
                    
                    self.db.add_warning(
                        chat_id=chat_id,
                        user_id=user_id,
                        admin_id=None,
                        reason=f"Utilisation du mot interdit: {word}"
                    )
                    
                except (BadRequest, Forbidden) as e:
                    self.logger.error(f"Erreur lors de la suppression de message: {e}")
                return
        
        if await self.detect_spam(update, context):
            try:
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🚫 Message supprimé: spam détecté."
                )
            except (BadRequest, Forbidden) as e:
                self.logger.error(f"Erreur lors de la suppression de spam: {e}")

    async def check_admin_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vérifie les permissions d'administrateur"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except (BadRequest, Forbidden) as e:
            self.logger.error(f"Erreur de vérification des permissions: {e}")
            return False
    
    async def get_target_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Récupère l'utilisateur cible pour les commandes de modération"""
        if not context.args:
            if update.message.reply_to_message:
                user = update.message.reply_to_message.from_user
                return {
                    'user_id': user.id,
                    'username': user.username,
                    'first_name': user.first_name
                }
            return None
        
        try:
            target = context.args[0]
            
            if target.isdigit():
                user_id = int(target)
                user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                return {
                    'user_id': user.user.id,
                    'username': user.user.username,
                    'first_name': user.user.first_name
                }
            
            if target.startswith('@'):
                username = target[1:]
                user_id = self.db.get_user_id_by_username(username)
                if user_id:
                    return {
                        'user_id': user_id,
                        'username': username,
                        'first_name': None
                    }
        except Exception as e:
            self.logger.error(f"Erreur get_target_user: {e}")
        
        return None
    
    async def detect_spam(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Détecte le spam dans les messages"""
        message = update.message
        user_id = update.effective_user.id
        
        recent_messages = self.db.get_recent_user_messages(user_id, minutes=5)
        if len(recent_messages) > 5:
            return True
        
        if message.text:
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, message.text)
            if urls and not self.db.is_trusted_domain(urls[0]):
                return True
        
        if message.text and len(set(message.text)) < len(message.text) * 0.3:
            return True
        
        return False

def setup(application: Application):
    """Configure les handlers de modération"""
    from utils.memory_full import db
    from utils.security import security_manager
    
    handler = ModerationHandler(db, security_manager)
    
    application.add_handler(CommandHandler("kick", handler.kick_command))
    application.add_handler(CommandHandler("ban", handler.ban_command))
    application.add_handler(CommandHandler("mute", handler.mute_command))
    application.add_handler(CommandHandler("unmute", handler.unmute_command))
    application.add_handler(CommandHandler("warn", handler.warn_command))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS, 
        handler.handle_message
    ))