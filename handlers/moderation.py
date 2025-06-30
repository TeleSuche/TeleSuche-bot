from datetime import datetime
"""
Gestionnaire des fonctions de modération
"""

import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ContextTypes
from telegram.error import BadRequest, Forbidden

class ModerationHandler:
    """Gestionnaire des commandes de modération"""
    
    def __init__(self, db, translations, security):
        self.db = db
        self.translations = translations
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
                until_date=datetime.now() + timedelta(seconds=30)  # Kick temporaire
            )
            
            # Log de l'action
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='kick',
                reason=context.args[1:] if len(context.args) > 1 else None
            )
            
            await update.message.reply_text(
                f"✅ {target_user['username']} a été expulsé du groupe."
            )
            
        except (BadRequest, Forbidden) as e:
            await update.message.reply_text(f"❌ Impossible d'expulser l'utilisateur: {e}")
    
    async def ban_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /ban - Bannir un utilisateur"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        # Durée du ban (par défaut permanente)
        ban_duration = None
        if len(context.args) > 1:
            try:
                duration_str = context.args[1]
                if duration_str.endswith('h'):
                    hours = int(duration_str[:-1])
                    ban_duration = datetime.now() + timedelta(hours=hours)
                elif duration_str.endswith('d'):
                    days = int(duration_str[:-1])
                    ban_duration = datetime.now() + timedelta(days=days)
            except ValueError:
                pass
        
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=target_user['user_id'],
                until_date=ban_duration
            )
            
            # Log de l'action
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='ban',
                reason=context.args[2:] if len(context.args) > 2 else None,
                duration=ban_duration
            )
            
            duration_text = f" pour {context.args[1]}" if ban_duration else " définitivement"
            await update.message.reply_text(
                f"🔨 {target_user['username']} a été banni{duration_text}."
            )
            
        except (BadRequest, Forbidden) as e:
            await update.message.reply_text(f"❌ Impossible de bannir l'utilisateur: {e}")
    
    async def mute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /mute - Réduire au silence"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        # Durée du mute (par défaut 1 heure)
        mute_duration = datetime.now() + timedelta(hours=1)
        if len(context.args) > 1:
            try:
                duration_str = context.args[1]
                if duration_str.endswith('m'):
                    minutes = int(duration_str[:-1])
                    mute_duration = datetime.now() + timedelta(minutes=minutes)
                elif duration_str.endswith('h'):
                    hours = int(duration_str[:-1])
                    mute_duration = datetime.now() + timedelta(hours=hours)
            except ValueError:
                pass
        
        try:
            # Restrictions pour le mute
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
            
            # Log de l'action
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='mute',
                reason=context.args[2:] if len(context.args) > 2 else None,
                duration=mute_duration
            )
            
            await update.message.reply_text(
                f"🔇 {target_user['username']} a été réduit au silence jusqu'à {mute_duration.strftime('%H:%M')}."
            )
            
        except (BadRequest, Forbidden) as e:
            await update.message.reply_text(f"❌ Impossible de réduire au silence: {e}")
    
    async def unmute_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /unmute - Retirer le silence"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        try:
            # Restaurer les permissions
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
            
            # Log de l'action
            self.db.log_moderation_action(
                chat_id=update.effective_chat.id,
                admin_id=update.effective_user.id,
                target_user_id=target_user['user_id'],
                action='unmute'
            )
            
            await update.message.reply_text(
                f"🔊 {target_user['username']} peut de nouveau parler."
            )
            
        except (BadRequest, Forbidden) as e:
            await update.message.reply_text(f"❌ Impossible de retirer le silence: {e}")
    
    async def warn_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /warn - Avertir un utilisateur"""
        if not await self.check_admin_permissions(update, context):
            return
        
        target_user = await self.get_target_user(update, context)
        if not target_user:
            await update.message.reply_text("❌ Utilisateur non trouvé ou non spécifié.")
            return
        
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Aucune raison spécifiée"
        
        # Ajouter l'avertissement
        warning_count = self.db.add_warning(
            chat_id=update.effective_chat.id,
            user_id=target_user['user_id'],
            admin_id=update.effective_user.id,
            reason=reason
        )
        
        # Vérifier le nombre d'avertissements
        max_warnings = self.db.get_group_setting(update.effective_chat.id, 'max_warnings', 3)
        
        if warning_count >= max_warnings:
            # Auto-ban après X avertissements
            try:
                await context.bot.ban_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=target_user['user_id']
                )
                
                await update.message.reply_text(
                    f"⚠️ {target_user['username']} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                    f"Raison: {reason}\n\n"
                    f"🔨 Utilisateur banni automatiquement (limite d'avertissements atteinte)."
                )
            except (BadRequest, Forbidden):
                await update.message.reply_text(
                    f"⚠️ {target_user['username']} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                    f"Raison: {reason}\n\n"
                    f"❌ Impossible de bannir automatiquement."
                )
        else:
            await update.message.reply_text(
                f"⚠️ {target_user['username']} a reçu un avertissement ({warning_count}/{max_warnings})\n"
                f"Raison: {reason}"
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Traite les messages pour la modération automatique"""
        if not update.message or not update.message.text:
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message_text = update.message.text.lower()
        
        # Vérifier les mots interdits
        banned_words = self.db.get_group_setting(chat_id, 'banned_words', [])
        for word in banned_words:
            if word.lower() in message_text:
                try:
                    await update.message.delete()
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Message supprimé: contenu interdit détecté.",
                        reply_to_message_id=None
                    )
                    
                    # Ajouter un avertissement automatique
                    self.db.add_warning(
                        chat_id=chat_id,
                        user_id=user_id,
                        admin_id=None,
                        reason=f"Utilisation du mot interdit: {word}"
                    )
                    
                except (BadRequest, Forbidden):
                    pass
                return
        
        # Détection de spam
        if await self.detect_spam(update, context):
            try:
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🚫 Message supprimé: spam détecté."
                )
            except (BadRequest, Forbidden):
                pass
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks de modération"""
        query = update.callback_query
        data = query.data
        
        await query.answer()
        
        if data.startswith("mod_kick_"):
            user_id = int(data.split("_")[2])
            await self.handle_kick_callback(query, user_id)
        elif data.startswith("mod_ban_"):
            user_id = int(data.split("_")[2])
            await self.handle_ban_callback(query, user_id)
        elif data.startswith("mod_warn_"):
            user_id = int(data.split("_")[2])
            await self.handle_warn_callback(query, user_id)
    
    async def check_admin_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Vérifie les permissions d'administrateur"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
        except (BadRequest, Forbidden):
            return False
    
    async def get_target_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Récupère l'utilisateur cible pour les commandes de modération"""
        if not context.args:
            # Vérifier si c'est une réponse à un message
            if update.message.reply_to_message:
                user = update.message.reply_to_message.from_user
                return {
                    'user_id': user.id,
                    'username': user.username or user.first_name
                }
            return None
        
        target = context.args[0]
        
        # Si c'est un ID numérique
        if target.isdigit():
            user_id = int(target)
            try:
                user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
                return {
                    'user_id': user_id,
                    'username': user.user.username or user.user.first_name
                }
            except (BadRequest, Forbidden):
                return None
        
        # Si c'est un username
        if target.startswith('@'):
            username = target[1:]
            # Rechercher dans la base de données locale
            user_id = self.db.get_user_id_by_username(username)
            if user_id:
                return {
                    'user_id': user_id,
                    'username': username
                }
        
        return None
    
    async def detect_spam(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Détecte le spam dans les messages"""
        message = update.message
        user_id = update.effective_user.id
        
        # Vérifier la répétition de messages
        recent_messages = self.db.get_recent_user_messages(user_id, minutes=5)
        if len(recent_messages) > 5:  # Plus de 5 messages en 5 minutes
            return True
        
        # Vérifier les liens suspects
        if message.text:
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, message.text)
            if urls and not self.db.is_trusted_domain(urls[0]):
                return True
        
        # Vérifier les caractères répétitifs
        if message.text and len(set(message.text)) < len(message.text) * 0.3:
            return True
        
        return False
    
    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gère l'arrivée de nouveaux membres"""
        for new_member in update.message.new_chat_members:
            # Message de bienvenue
            welcome_message = self.db.get_group_setting(
                update.effective_chat.id, 
                'welcome_message', 
                "Bienvenue dans le groupe!"
            )
            
            # Captcha si activé
            if self.db.get_group_setting(update.effective_chat.id, 'captcha_enabled', False):
                await self.send_captcha(update, context, new_member)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{welcome_message}\n\nBienvenue {new_member.first_name}!"
                )
    
    async def send_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """Envoie un captcha au nouvel utilisateur"""
        import random
        
        # Générer un captcha simple
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        result = num1 + num2
        
        # Stocker la réponse
        self.db.store_captcha(update.effective_chat.id, user.id, result)
        
        keyboard = [
            [InlineKeyboardButton("Résoudre le captcha", callback_data=f"captcha_{user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🤖 {user.first_name}, résolvez ce captcha pour confirmer que vous n'êtes pas un robot:\n\n"
                 f"❓ Combien font {num1} + {num2} ?",
            reply_markup=reply_markup
        )
