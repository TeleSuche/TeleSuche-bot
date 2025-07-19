"""
Gestionnaire des fonctions utilisateur de base
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class UserHandler:
    """Gestionnaire des commandes utilisateur de base"""
    
    def __init__(self, db, translations):
        self.db = db
        self.translations = translations
        self.logger = logging.getLogger(__name__)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /start - Accueil et inscription"""
        user = update.effective_user
        user_id = user.id
        
        # Vérifier si c'est un parrainage
        referral_code = None
        if context.args and context.args[0].startswith('ref_'):
            referral_code = context.args[0].replace('ref_', '')
        
        # Enregistrer ou mettre à jour l'utilisateur
        is_new_user = self.db.create_or_update_user(
            user_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        # Traiter le parrainage si applicable
        if is_new_user and referral_code:
            from handlers.referral import ReferralHandler
            referral_handler = ReferralHandler(self.db, self.translations)
            referral_result = await referral_handler.process_referral_signup(user_id, referral_code)
            
            if referral_result['success']:
                welcome_text = f"""🎉 **Bienvenue dans TeleSuche!**

Félicitations! Vous avez été parrainé et recevez **{referral_result['bonus_new_user']} crédits bonus**!

🤖 **TeleSuche** est votre assistant Telegram tout-en-un:"""
            else:
                welcome_text = "🎉 **Bienvenue dans TeleSuche!**\n\n🤖 **TeleSuche** est votre assistant Telegram tout-en-un:"
        else:
            if is_new_user:
                welcome_text = "🎉 **Bienvenue dans TeleSuche!**\n\n🤖 **TeleSuche** est votre assistant Telegram tout-en-un:"
            else:
                welcome_text = f"👋 **Bon retour, {user.first_name}!**\n\n🤖 **TeleSuche** - Votre assistant Telegram:"
        
        features_text = """
🛡️ **Modération intelligente**
• Gestion automatique des spams
• Commandes de modération avancées
• Système d'avertissements

🏪 **Boutique intégrée**
• Achat de crédits et produits
• Système de paiement sécurisé
• Abonnements Premium

🔍 **Recherche avancée**
• Indexation de documents
• Recherche textuelle intelligente
• Filtres personnalisés

💰 **Système de parrainage**
• Gagnez des crédits en invitant
• Commissions sur les achats
• Programmes de fidélité

🤖 **Multi-bot**
• Créez vos propres bots
• Templates personnalisables
• Gestion centralisée"""
        
        # Afficher le solde de crédits
        credits = self.db.get_user_credits(user_id)
        premium_status = self.db.get_premium_status(user_id)
        
        status_text = f"\n💰 **Vos crédits:** {credits}\n"
        if premium_status['is_premium']:
            days_left = (premium_status['expiry_date'] - datetime.now()).days
            status_text += f"⭐ **Premium actif** ({days_left} jours restants)"
        else:
            status_text += "🔓 **Compte gratuit** - Passez Premium pour plus de fonctionnalités!"
        
        full_text = welcome_text + features_text + status_text
        
        # Clavier principal
        keyboard = [
            [
                InlineKeyboardButton("🏪 Boutique", callback_data="main_shop"),
                InlineKeyboardButton("👤 Mon Profil", callback_data="main_profile")
            ],
            [
                InlineKeyboardButton("🔍 Recherche", callback_data="main_search"),
                InlineKeyboardButton("🤝 Parrainage", callback_data="main_referral")
            ],
            [
                InlineKeyboardButton("⭐ Premium", callback_data="main_premium"),
                InlineKeyboardButton("🤖 Créer un bot", callback_data="main_create_bot")
            ],
            [
                InlineKeyboardButton("❓ Aide", callback_data="main_help"),
                InlineKeyboardButton("⚙️ Paramètres", callback_data="main_settings")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            full_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /help - Aide et documentation"""
        text = """❓ **Aide TeleSuche**

📚 **Commandes principales:**

**👤 Utilisateur:**
• `/start` - Démarrer le bot
• `/profile` - Voir votre profil
• `/me` - Informations rapides
• `/credits` - Gérer vos crédits

**🔍 Recherche:**
• `/search <terme>` - Rechercher des documents
• `/index` - Gérer l'indexation

**🏪 Boutique:**
• `/shop` - Accéder à la boutique
• `/buy <produit>` - Acheter un produit
• `/subscribe` - Gérer les abonnements

**🤝 Parrainage:**
• `/referral` - Dashboard parrainage
• `/invite` - Inviter des amis
• `/filleuls` - Voir vos filleuls

**🛡️ Modération (Admins):**
• `/kick @user` - Expulser
• `/ban @user [durée]` - Bannir
• `/mute @user [durée]` - Réduire au silence
• `/warn @user` - Avertir

**⚙️ Administration:**
• `/config` - Configuration
• `/admin` - Panel admin
• `/stats` - Statistiques
• `/logs` - Voir les logs

🔗 **Liens utiles:**
• [Documentation complète](https://telesuche.com/docs)
• [Support technique](https://t.me/telesuchesupport)
• [Communauté](https://t.me/telesuchegroup)"""
        
        keyboard = [
            [
                InlineKeyboardButton("📖 Guide débutant", callback_data="help_beginner"),
                InlineKeyboardButton("🔧 Guide avancé", callback_data="help_advanced")
            ],
            [
                InlineKeyboardButton("🎥 Tutoriels vidéo", callback_data="help_videos"),
                InlineKeyboardButton("💬 Support live", callback_data="help_support")
            ],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /profile - Profil utilisateur détaillé"""
        user_id = update.effective_user.id
        profile = self.db.get_user_profile(user_id)
        
        if not profile:
            await update.message.reply_text("❌ Profil non trouvé. Utilisez /start pour vous inscrire.")
            return
        
        # Calculer les statistiques
        stats = self.db.get_user_statistics(user_id)
        premium_status = self.db.get_premium_status(user_id)
        
        # Format de la date d'inscription
        join_date = profile['created_at'].strftime('%d/%m/%Y') if profile['created_at'] else 'Inconnu'
        
        text = f"""👤 **Profil de {profile['first_name']}**

📊 **Informations générales:**
• ID: `{user_id}`
• Username: @{profile['username'] or 'Non défini'}
• Membre depuis: {join_date}
• Langue: {profile['language_code'] or 'Non définie'}

💰 **Finances:**
• Crédits actuels: **{profile['credits']}**
• Total dépensé: {stats['total_spent']}€
• Économies réalisées: {stats['savings']}€

⭐ **Abonnement:**"""
        
        if premium_status['is_premium']:
            expiry = premium_status['expiry_date'].strftime('%d/%m/%Y')
            text += f"""
• Statut: **Premium Actif** ⭐
• Expire le: {expiry}
• Type: {premium_status.get('plan_type', 'Premium')}"""
        else:
            text += f"""
• Statut: **Gratuit**
• Upgrade disponible: Premium dès 9.99€/mois"""
        
        text += f"""

📈 **Activité:**
• Commandes utilisées: {stats['commands_used']}
• Recherches effectuées: {stats['searches_performed']}
• Documents indexés: {stats['documents_indexed']}
• Dernière activité: {stats['last_activity']}

🤝 **Parrainage:**
• Filleuls: {stats['total_referrals']}
• Gains du parrainage: {stats['referral_earnings']} crédits
• Niveau: {stats['referral_tier']}

🏆 **Accomplissements:**
{self.format_achievements(stats['achievements'])}"""
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ Modifier profil", callback_data="profile_edit"),
                InlineKeyboardButton("🔒 Confidentialité", callback_data="profile_privacy")
            ],
            [
                InlineKeyboardButton("📊 Stats détaillées", callback_data="profile_detailed_stats"),
                InlineKeyboardButton("🏆 Badges", callback_data="profile_badges")
            ],
            [
                InlineKeyboardButton("⚙️ Paramètres", callback_data="profile_settings"),
                InlineKeyboardButton("📤 Exporter données", callback_data="profile_export")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def me_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /me - Informations rapides"""
        user_id = update.effective_user.id
        
        # Récupérer les informations essentielles
        credits = self.db.get_user_credits(user_id)
        premium_status = self.db.get_premium_status(user_id)
        daily_stats = self.db.get_daily_user_stats(user_id)
        
        text = f"""⚡ **Aperçu Rapide**

💰 **Crédits:** {credits}
⭐ **Statut:** {'Premium' if premium_status['is_premium'] else 'Gratuit'}

📊 **Aujourd'hui:**
• Recherches: {daily_stats['searches_today']}/10 {'(illimitées)' if premium_status['is_premium'] else ''}
• Commandes: {daily_stats['commands_today']}
• Documents indexés: {daily_stats['documents_today']}

🎯 **Actions rapides:**"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Rechercher", callback_data="quick_search"),
                InlineKeyboardButton("🏪 Boutique", callback_data="quick_shop")
            ],
            [
                InlineKeyboardButton("🤝 Inviter", callback_data="quick_invite"),
                InlineKeyboardButton("📊 Stats", callback_data="quick_stats")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks utilisateur"""
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        await query.answer()
        
        if data == "main_shop":
            from handlers.shop import ShopHandler
            shop_handler = ShopHandler(self.db, self.translations)
            await shop_handler.show_main_shop(query)
        
        elif data == "main_profile":
            await self.show_profile_callback(query)
        
        elif data == "main_search":
            await self.show_search_menu(query)
        
        elif data == "main_referral":
            from handlers.referral import ReferralHandler
            referral_handler = ReferralHandler(self.db, self.translations)
            await referral_handler.share_referral_link(query)
        
        elif data == "main_premium":
            from handlers.subscription import SubscriptionHandler
            subscription_handler = SubscriptionHandler(self.db, self.translations)
            await subscription_handler.show_subscription_options_callback(query)
        
        elif data == "main_create_bot":
            await self.show_create_bot_menu(query)
        
        elif data == "main_help":
            await self.show_help_menu(query)
        
        elif data == "main_settings":
            await self.show_settings_menu(query)
        
        elif data.startswith("profile_"):
            await self.handle_profile_callback(query, data)
        
        elif data.startswith("quick_"):
            await self.handle_quick_action(query, data)
        
        elif data.startswith("help_"):
            await self.handle_help_callback(query, data)
        
        elif data.startswith("settings_"):
            await self.handle_settings_callback(query, data)
    
    async def show_profile_callback(self, query):
        """Affiche le profil via callback"""
        user_id = query.from_user.id
        profile = self.db.get_user_profile(user_id)
        
        text = f"""👤 **Votre Profil**

📋 **Informations:**
• Nom: {profile['first_name']} {profile['last_name'] or ''}
• Username: @{profile['username'] or 'Non défini'}
• Crédits: {profile['credits']}
• Membre depuis: {profile['created_at'].strftime('%d/%m/%Y')}

⚙️ **Paramètres rapides:**"""
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ Modifier nom", callback_data="profile_edit_name"),
                InlineKeyboardButton("🌐 Changer langue", callback_data="profile_change_language")
            ],
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="profile_notifications"),
                InlineKeyboardButton("🔒 Confidentialité", callback_data="profile_privacy")
            ],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_search_menu(self, query):
        """Affiche le menu de recherche"""
        user_id = query.from_user.id
        search_stats = self.db.get_user_search_stats(user_id)
        
        text = f"""🔍 **Centre de Recherche**

📊 **Vos statistiques:**
• Documents indexés: {search_stats['total_documents']}
• Recherches ce mois: {search_stats['monthly_searches']}
• Taille totale: {round(search_stats['total_size'] / (1024*1024), 2)} MB

🎯 **Actions disponibles:**"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Nouvelle recherche", callback_data="search_new"),
                InlineKeyboardButton("📄 Indexer document", callback_data="search_index_guide")
            ],
            [
                InlineKeyboardButton("📂 Mes documents", callback_data="search_my_docs"),
                InlineKeyboardButton("📊 Statistiques", callback_data="search_stats")
            ],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_create_bot_menu(self, query):
        """Affiche le menu de création de bot"""
        user_id = query.from_user.id
        user_bots = self.db.get_user_bots(user_id)
        is_premium = self.db.is_premium_user(user_id)
        
        max_bots = 999 if is_premium else 3
        current_bots = len(user_bots)
        
        text = f"""🤖 **Création de Bots**

📊 **Votre quota:**
• Bots créés: {current_bots}/{max_bots}
• Bots actifs: {sum(1 for bot in user_bots if bot['is_active'])}

🎯 **Bots disponibles:**"""
        
        if user_bots:
            for bot in user_bots[:5]:
                status = "🟢" if bot['is_active'] else "🔴"
                text += f"\n{status} {bot['name']} (@{bot['username']})"
        
        keyboard = []
        
        if current_bots < max_bots:
            keyboard.append([InlineKeyboardButton("➕ Créer un nouveau bot", callback_data="bot_create_new")])
        
        if user_bots:
            keyboard.append([InlineKeyboardButton("⚙️ Gérer mes bots", callback_data="bot_manage")])
        
        keyboard.extend([
            [InlineKeyboardButton("📖 Guide création", callback_data="bot_guide")],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_help_menu(self, query):
        """Affiche le menu d'aide"""
        text = """❓ **Centre d'Aide TeleSuche**

🎯 **Que voulez-vous apprendre?**"""
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Premiers pas", callback_data="help_getting_started"),
                InlineKeyboardButton("🔍 Utiliser la recherche", callback_data="help_search")
            ],
            [
                InlineKeyboardButton("🏪 Acheter des crédits", callback_data="help_shop"),
                InlineKeyboardButton("🤝 Système de parrainage", callback_data="help_referral")
            ],
            [
                InlineKeyboardButton("🤖 Créer des bots", callback_data="help_bots"),
                InlineKeyboardButton("⭐ Avantages Premium", callback_data="help_premium")
            ],
            [
                InlineKeyboardButton("🛡️ Modération", callback_data="help_moderation"),
                InlineKeyboardButton("💬 Contact support", callback_data="help_contact")
            ],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_settings_menu(self, query):
        """Affiche le menu des paramètres"""
        user_id = query.from_user.id
        settings = self.db.get_user_settings(user_id)
        
        text = f"""⚙️ **Paramètres**

🔔 **Notifications:**
• Messages privés: {'✅' if settings.get('pm_notifications', True) else '❌'}
• Alertes parrainage: {'✅' if settings.get('referral_alerts', True) else '❌'}
• Rappels Premium: {'✅' if settings.get('premium_reminders', True) else '❌'}

🌐 **Interface:**
• Langue: {settings.get('language', 'Français')}
• Thème: {settings.get('theme', 'Standard')}
• Format date: {settings.get('date_format', 'DD/MM/YYYY')}

🔒 **Confidentialité:**
• Profil public: {'✅' if settings.get('public_profile', False) else '❌'}
• Stats visibles: {'✅' if settings.get('visible_stats', True) else '❌'}"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔔 Notifications", callback_data="settings_notifications"),
                InlineKeyboardButton("🌐 Langue", callback_data="settings_language")
            ],
            [
                InlineKeyboardButton("🔒 Confidentialité", callback_data="settings_privacy"),
                InlineKeyboardButton("📊 Données", callback_data="settings_data")
            ],
            [
                InlineKeyboardButton("🎨 Interface", callback_data="settings_interface"),
                InlineKeyboardButton("🔧 Avancé", callback_data="settings_advanced")
            ],
            [InlineKeyboardButton("🔙 Menu principal", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def format_achievements(self, achievements):
        """Formate la liste des accomplissements"""
        if not achievements:
            return "Aucun accomplissement pour le moment"
        
        formatted = ""
        for achievement in achievements[:5]:
            formatted += f"🏆 {achievement['name']} - {achievement['description']}\n"
        
        return formatted
    
    async def handle_profile_callback(self, query, data):
        """Gère les callbacks du profil"""
        if data == "profile_edit_name":
            await query.edit_message_text(
                "✏️ **Modification du nom**\n\n"
                "Pour modifier votre nom, envoyez simplement un message avec votre nouveau nom.\n"
                "Exemple: `Jean Dupont`",
                parse_mode='Markdown'
            )
        elif data == "profile_change_language":
            await self.show_language_selection(query)
        elif data == "profile_notifications":
            await self.show_notification_settings(query)
    
    async def handle_quick_action(self, query, data):
        """Gère les actions rapides"""
        if data == "quick_search":
            await query.edit_message_text(
                "🔍 **Recherche rapide**\n\n"
                "Tapez `/search` suivi de votre terme de recherche.\n"
                "Exemple: `/search contrat`"
            )
        elif data == "quick_shop":
            from handlers.shop import ShopHandler
            shop_handler = ShopHandler(self.db, self.translations)
            await shop_handler.show_main_shop(query)
        elif data == "quick_invite":
            from handlers.referral import ReferralHandler
            referral_handler = ReferralHandler(self.db, self.translations)
            await referral_handler.share_referral_link(query)
    
    async def show_language_selection(self, query):
        """Affiche la sélection de langue"""
        text = "🌐 **Choisissez votre langue:**"
        
        languages = [
            ("🇫🇷 Français", "lang_fr"),
            ("🇬🇧 English", "lang_en"),
            ("🇪🇸 Español", "lang_es"),
            ("🇩🇪 Deutsch", "lang_de"),
            ("🇮🇹 Italiano", "lang_it"),
            ("🇷🇺 Русский", "lang_ru")
        ]
        
        keyboard = []
        for lang_name, lang_code in languages:
            keyboard.append([InlineKeyboardButton(lang_name, callback_data=lang_code)])
        
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data="main_profile")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
