import logging
logger = logging.getLogger(__name__)
from datetime import datetime
"""
Gestionnaire des fonctions administrateur
"""

import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class AdminHandler:
    """Gestionnaire des commandes administrateur"""
    
    def __init__(self, db, translations):
        self.db = db
        self.translations = translations
        self.logger = logging.getLogger(__name__)
    
    def is_admin(self, user_id):
        """Vérifie si l'utilisateur est administrateur"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            return user_id in config.get('admin_users', [])
        except:
            return False
    
    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /config - Configuration interactive"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Accès refusé. Commande réservée aux administrateurs.")
            return
        
        keyboard = [
            [InlineKeyboardButton("🔧 Configuration générale", callback_data="admin_config_general")],
            [InlineKeyboardButton("🛡️ Modération", callback_data="admin_config_moderation")],
            [InlineKeyboardButton("🏪 Boutique", callback_data="admin_config_shop")],
            [InlineKeyboardButton("💰 Abonnements", callback_data="admin_config_subscription")],
            [InlineKeyboardButton("🔍 Recherche", callback_data="admin_config_search")],
            [InlineKeyboardButton("📊 Statistiques", callback_data="admin_stats")],
            [InlineKeyboardButton("📋 Logs", callback_data="admin_logs")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """🔧 **Panel de Configuration**

Sélectionnez le module à configurer:"""
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /admin - Panel administrateur principal"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Accès refusé.")
            return
        
        # Récupération des statistiques
        stats = self.get_admin_stats()
        
        text = f"""👨‍💼 **Dashboard Administrateur**

📊 **Statistiques générales:**
• Utilisateurs totaux: {stats['total_users']}
• Utilisateurs actifs (7j): {stats['active_users']}
• Groupes gérés: {stats['total_groups']}
• Commandes exécutées: {stats['total_commands']}

💰 **Finances:**
• Revenus totaux: {stats['total_revenue']}€
• Abonnements actifs: {stats['active_subscriptions']}
• Crédits vendus: {stats['credits_sold']}

🔍 **Recherche:**
• Documents indexés: {stats['indexed_documents']}
• Recherches effectuées: {stats['total_searches']}

⚡ **Système:**
• Uptime: {stats['uptime']}
• Dernière sauvegarde: {stats['last_backup']}"""
        
        keyboard = [
            [InlineKeyboardButton("📊 Stats détaillées", callback_data="admin_detailed_stats")],
            [InlineKeyboardButton("👥 Gestion utilisateurs", callback_data="admin_users")],
            [InlineKeyboardButton("🔧 Configuration", callback_data="admin_config")],
            [InlineKeyboardButton("📋 Export données", callback_data="admin_export")],
            [InlineKeyboardButton("🔄 Maintenance", callback_data="admin_maintenance")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /stats - Affichage des statistiques"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Accès refusé.")
            return
        
        stats = self.get_detailed_stats()
        
        text = f"""📈 **Statistiques Détaillées**

📅 **Aujourd'hui:**
• Nouveaux utilisateurs: {stats['today']['new_users']}
• Commandes exécutées: {stats['today']['commands']}
• Achats effectués: {stats['today']['purchases']}

📅 **Cette semaine:**
• Nouveaux utilisateurs: {stats['week']['new_users']}
• Revenus: {stats['week']['revenue']}€
• Messages traités: {stats['week']['messages']}

📅 **Ce mois:**
• Croissance utilisateurs: +{stats['month']['user_growth']}%
• Revenus: {stats['month']['revenue']}€
• Taux de conversion: {stats['month']['conversion_rate']}%

🏆 **Top commandes:**
{self.format_top_commands(stats['top_commands'])}"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /logs - Affichage des logs"""
        user_id = update.effective_user.id
        
        if not self.is_admin(user_id):
            await update.message.reply_text("❌ Accès refusé.")
            return
        
        try:
            # Lecture des derniers logs
            logs = self.get_recent_logs(50)
            
            if not logs:
                await update.message.reply_text("📋 Aucun log récent.")
                return
            
            text = "📋 **Logs récents:**\n\n"
            for log in logs:
                text += f"`{log['timestamp']}` - {log['level']} - {log['message']}\n"
            
            # Découper si trop long
            if len(text) > 4000:
                text = text[:4000] + "\n... (tronqué)"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la lecture des logs: {e}")
            await update.message.reply_text("❌ Erreur lors de la lecture des logs.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks admin"""
        query = update.callback_query
        data = query.data
        
        await query.answer()
        
        if data == "admin_config_general":
            await self.show_general_config(query)
        elif data == "admin_config_moderation":
            await self.show_moderation_config(query)
        elif data == "admin_config_shop":
            await self.show_shop_config(query)
        elif data == "admin_stats":
            await self.show_detailed_stats(query)
        elif data == "admin_export":
            await self.export_data(query)
        elif data == "admin_maintenance":
            await self.show_maintenance_menu(query)
    
    async def show_general_config(self, query):
        """Affiche la configuration générale"""
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        text = f"""🔧 **Configuration Générale**

🌐 **Langues:**
• Langue par défaut: {config['default_language']}
• Langues supportées: {', '.join(config['supported_languages'])}

📊 **Base de données:**
• Chemin: {config['database_path']}
• Niveau de log: {config['log_level']}

👥 **Administrateurs:**
• Nombre: {len(config['admin_users'])}"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ Modifier langue", callback_data="admin_edit_language")],
            [InlineKeyboardButton("👥 Gérer admins", callback_data="admin_manage_admins")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_config")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_moderation_config(self, query):
        """Affiche la configuration de modération"""
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        mod_config = config.get('moderation', {})
        
        text = f"""🛡️ **Configuration Modération**

⚙️ **Paramètres:**
• Modération activée: {'✅' if mod_config.get('enabled') else '❌'}
• Suppression auto spam: {'✅' if mod_config.get('auto_delete_spam') else '❌'}
• Captcha activé: {'✅' if mod_config.get('captcha_enabled') else '❌'}
• Avertissements max: {mod_config.get('max_warnings', 3)}

📝 **Message de bienvenue:**
{mod_config.get('welcome_message', 'Non défini')}

🚫 **Mots interdits:**
{len(mod_config.get('banned_words', []))} mots configurés"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ Modifier message", callback_data="admin_edit_welcome")],
            [InlineKeyboardButton("🚫 Gérer mots interdits", callback_data="admin_banned_words")],
            [InlineKeyboardButton("⚙️ Paramètres", callback_data="admin_mod_settings")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_config")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def get_admin_stats(self):
        """Récupère les statistiques pour l'admin"""
        try:
            # Simulation des statistiques
            return {
                'total_users': self.db.get_user_count(),
                'active_users': self.db.get_active_users_count(7),
                'total_groups': self.db.get_group_count(),
                'total_commands': self.db.get_command_count(),
                'total_revenue': self.db.get_total_revenue(),
                'active_subscriptions': self.db.get_active_subscriptions_count(),
                'credits_sold': self.db.get_credits_sold(),
                'indexed_documents': self.db.get_indexed_documents_count(),
                'total_searches': self.db.get_search_count(),
                'uptime': self.get_uptime(),
                'last_backup': self.get_last_backup()
            }
        except Exception as e:
            self.logger.error(f"Erreur récupération stats admin: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'total_groups': 0,
                'total_commands': 0,
                'total_revenue': 0.0,
                'active_subscriptions': 0,
                'credits_sold': 0,
                'indexed_documents': 0,
                'total_searches': 0,
                'uptime': '0h 0m',
                'last_backup': 'Jamais'
            }
    
    def get_detailed_stats(self):
        """Récupère les statistiques détaillées"""
        # Simulation des statistiques détaillées
        return {
            'today': {
                'new_users': 12,
                'commands': 245,
                'purchases': 8
            },
            'week': {
                'new_users': 87,
                'revenue': 125.50,
                'messages': 1850
            },
            'month': {
                'user_growth': 23,
                'revenue': 450.75,
                'conversion_rate': 12.5
            },
            'top_commands': [
                {'command': '/start', 'count': 150},
                {'command': '/shop', 'count': 89},
                {'command': '/search', 'count': 67}
            ]
        }
    
    def get_recent_logs(self, limit=50):
        """Récupère les logs récents"""
        try:
            # Simulation de logs
            logs = []
            for i in range(min(limit, 10)):  # Limité pour démo
                logs.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'level': 'INFO',
                    'message': f'Log d\'exemple {i+1}'
                })
            return logs
        except Exception as e:
            self.logger.error(f"Erreur lecture logs: {e}")
            return []
    
    def format_top_commands(self, commands):
        """Formate les top commandes"""
        result = ""
        for i, cmd in enumerate(commands[:5], 1):
            result += f"{i}. {cmd['command']}: {cmd['count']} utilisations\n"
        return result
    
    def get_uptime(self):
        """Calcule l'uptime du bot"""
        # Simulation de l'uptime
        return "2h 34m"
    
    def get_last_backup(self):
        """Récupère la date de la dernière sauvegarde"""
        # Simulation
        return "Il y a 4 heures"
    
    async def export_data(self, query):
        """Exporte les données"""
        await query.edit_message_text(
            "📤 **Export des données**\n\n" +
            "Export en cours... Cette fonctionnalité sera bientôt disponible.",
            parse_mode='Markdown'
        )
    
    async def show_maintenance_menu(self, query):
        """Affiche le menu de maintenance"""
        text = """🔧 **Menu Maintenance**

Sélectionnez une action:"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Redémarrer bot", callback_data="admin_restart")],
            [InlineKeyboardButton("💾 Sauvegarde DB", callback_data="admin_backup")],
            [InlineKeyboardButton("🧹 Nettoyer logs", callback_data="admin_clean_logs")],
            [InlineKeyboardButton("📊 Optimiser DB", callback_data="admin_optimize_db")],
            [InlineKeyboardButton("🔙 Retour", callback_data="admin_config")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
