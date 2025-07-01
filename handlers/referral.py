"""
Gestionnaire du système de parrainage
"""

import logging
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class ReferralHandler:
    """Gestionnaire du système de parrainage"""
    
    def __init__(self, db, translations):
        self.db = db
        self.translations = translations
        self.logger = logging.getLogger(__name__)
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /referral - Dashboard de parrainage"""
        user_id = update.effective_user.id
        
        # Récupérer les statistiques de parrainage
        stats = self.db.get_referral_stats(user_id)
        referral_link = self.generate_referral_link(user_id)
        
        text = f"""🤝 **Votre Programme de Parrainage**

🔗 **Votre lien de parrainage:**
`{referral_link}`

📊 **Vos statistiques:**
• Filleuls inscrits: **{stats['total_referrals']}**
• Filleuls actifs: **{stats['active_referrals']}**
• Gains totaux: **{stats['total_earnings']} crédits**
• Ce mois: **{stats['monthly_earnings']} crédits**

💰 **Récompenses gagnées:**
• Par inscription: {stats['signup_bonus']} crédits
• Commissions: {stats['commission_rate']}% des achats
• Bonus de niveau: {stats['tier_bonus']} crédits

🏆 **Votre niveau:** {stats['tier_name']}
{self.get_tier_benefits(stats['tier_level'])}"""
        
        keyboard = [
            [InlineKeyboardButton("📤 Partager le lien", callback_data="ref_share")],
            [InlineKeyboardButton("👥 Mes filleuls", callback_data="ref_filleuls")],
            [InlineKeyboardButton("🎯 Missions bonus", callback_data="ref_missions")],
            [InlineKeyboardButton("🏆 Classement", callback_data="ref_leaderboard")],
            [InlineKeyboardButton("💡 Comment ça marche?", callback_data="ref_how_it_works")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /invite - Générer un lien d'invitation"""
        user_id = update.effective_user.id
        referral_link = self.generate_referral_link(user_id)
        
        text = f"""📤 **Invitez vos amis!**

🔗 Votre lien personnel:
`{referral_link}`

🎁 **Récompenses pour vous et vos amis:**
• Votre ami reçoit: 50 crédits bonus
• Vous recevez: 100 crédits par parrainage
• Bonus récurrent: 10% de leurs achats

💡 **Conseils pour réussir:**
• Partagez dans vos groupes actifs
• Expliquez les avantages de TeleSuche
• Aidez vos filleuls à démarrer

🏆 **Objectifs de parrainage:**
• 5 filleuls → Badge Bronze + 250 crédits
• 15 filleuls → Badge Argent + 750 crédits
• 50 filleuls → Badge Or + 2500 crédits"""
        
        keyboard = [
            [
                InlineKeyboardButton("📱 Partager", switch_inline_query=f"🤖 Découvrez TeleSuche! {referral_link}"),
                InlineKeyboardButton("📋 Copier", callback_data="ref_copy_link")
            ],
            [InlineKeyboardButton("🎯 Voir mes stats", callback_data="ref_stats")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def filleuls_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Commande /filleuls - Liste des filleuls"""
        user_id = update.effective_user.id
        filleuls = self.db.get_user_referrals(user_id, limit=20)
        
        if not filleuls:
            text = """👥 **Vos Filleuls**

Aucun filleul pour le moment.

🚀 **Commencez à inviter:**
Utilisez /invite pour obtenir votre lien de parrainage et commencer à gagner des crédits!"""
        else:
            text = f"""👥 **Vos Filleuls** ({len(filleuls)})

"""
            for i, filleul in enumerate(filleuls[:10], 1):
                status_emoji = "🟢" if filleul['is_active'] else "⚫"
                earnings = filleul['total_earnings']
                text += f"{i}. {status_emoji} {filleul['username']} ({earnings} crédits générés)\n"
                text += f"   Inscrit le: {filleul['join_date']}\n\n"
            
            if len(filleuls) > 10:
                text += f"... et {len(filleuls) - 10} autres filleuls"
        
        total_earnings = sum(f['total_earnings'] for f in filleuls)
        text += f"\n💰 **Total des gains:** {total_earnings} crédits"
        
        keyboard = [
            [InlineKeyboardButton("📤 Inviter plus d'amis", callback_data="ref_invite_more")],
            [InlineKeyboardButton("🎁 Récompenser filleuls", callback_data="ref_reward_referrals")],
            [InlineKeyboardButton("📊 Analytics détaillés", callback_data="ref_analytics")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Gestionnaire des callbacks de parrainage"""
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id
        
        await query.answer()
        
        if data == "ref_share":
            await self.share_referral_link(query)
        elif data == "ref_filleuls":
            await self.show_filleuls(query)
        elif data == "ref_missions":
            await self.show_missions(query)
        elif data == "ref_leaderboard":
            await self.show_leaderboard(query)
        elif data == "ref_how_it_works":
            await self.explain_referral_system(query)
        elif data == "ref_copy_link":
            await self.copy_referral_link(query)
        elif data == "ref_stats":
            await self.show_detailed_stats(query)
        elif data == "ref_invite_more":
            await self.invite_more_friends(query)
        elif data == "ref_reward_referrals":
            await self.reward_referrals(query)
        elif data == "ref_analytics":
            await self.show_analytics(query)
        elif data.startswith("ref_mission_"):
            mission_id = data.split("_")[2]
            await self.complete_mission(query, mission_id)
    
    async def share_referral_link(self, query):
        """Partage le lien de parrainage"""
        user_id = query.from_user.id
        referral_link = self.generate_referral_link(user_id)
        
        text = f"""📤 **Partagez votre lien**

🔗 Lien de parrainage:
`{referral_link}`

💬 **Messages prêts à partager:**

1️⃣ **Pour Telegram:**
"🤖 Découvrez TeleSuche, le bot multifonctionnel ultime! 
Modération, boutique, recherche avancée et bien plus.
Inscrivez-vous avec mon lien: {referral_link}"

2️⃣ **Pour les réseaux sociaux:**
"🚀 TeleSuche révolutionne la gestion Telegram! 
Bot intelligent avec IA, e-commerce intégré, modération automatique.
Rejoignez-nous: {referral_link}"

3️⃣ **Pour les groupes techniques:**
"⚡ TeleSuche: Solution complète pour administrateurs Telegram.
API avancée, analytics, multi-bots, recherche instantanée.
Testez gratuitement: {referral_link}" """
        
        keyboard = [
            [InlineKeyboardButton("📱 Partager sur Telegram", 
                                switch_inline_query=f"🤖 Découvrez TeleSuche! {referral_link}")],
            [InlineKeyboardButton("📋 Copier le lien", callback_data="ref_copy_link")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_filleuls(self, query):
        """Affiche la liste des filleuls"""
        user_id = query.from_user.id
        filleuls = self.db.get_user_referrals(user_id, limit=15)
        
        if not filleuls:
            text = """👥 **Vos Filleuls**

Aucun filleul inscrit pour le moment.

🎯 **Stratégies de parrainage:**
• Partagez dans vos groupes actifs
• Expliquez les avantages uniques
• Offrez de l'aide aux nouveaux utilisateurs
• Créez du contenu sur TeleSuche"""
        else:
            text = f"""👥 **Vos Filleuls** ({len(filleuls)} total)

📊 **Résumé:**
• Actifs ce mois: {sum(1 for f in filleuls if f['is_active'])}
• Gains totaux: {sum(f['total_earnings'] for f in filleuls)} crédits
• Meilleur filleul: {max(filleuls, key=lambda x: x['total_earnings'])['username']}

👥 **Liste détaillée:**
"""
            for i, filleul in enumerate(filleuls[:8], 1):
                status_emoji = "🟢" if filleul['is_active'] else "⚫"
                level_emoji = self.get_level_emoji(filleul['level'])
                text += f"{i}. {status_emoji} {level_emoji} {filleul['username']}\n"
                text += f"   💰 {filleul['total_earnings']} crédits | 📅 {filleul['join_date']}\n"
        
        keyboard = [
            [InlineKeyboardButton("🎁 Envoyer bonus", callback_data="ref_send_bonus")],
            [InlineKeyboardButton("📧 Message groupé", callback_data="ref_group_message")],
            [InlineKeyboardButton("📈 Croissance", callback_data="ref_growth_chart")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_missions(self, query):
        """Affiche les missions de parrainage"""
        user_id = query.from_user.id
        missions = self.db.get_referral_missions(user_id)
        
        text = """🎯 **Missions de Parrainage**

Complétez ces défis pour gagner des bonus supplémentaires!

"""
        
        active_missions = [
            {
                'id': 'first_5',
                'title': 'Premier Groupe',
                'description': 'Invitez 5 personnes',
                'reward': 250,
                'progress': missions.get('total_referrals', 0),
                'target': 5
            },
            {
                'id': 'active_month',
                'title': 'Mois Actif',
                'description': '3 filleuls actifs ce mois',
                'reward': 150,
                'progress': missions.get('active_this_month', 0),
                'target': 3
            },
            {
                'id': 'premium_convert',
                'title': 'Conversion Premium',
                'description': '1 filleul devient Premium',
                'reward': 500,
                'progress': missions.get('premium_converts', 0),
                'target': 1
            },
            {
                'id': 'social_share',
                'title': 'Influenceur Social',
                'description': 'Partagez sur 3 plateformes',
                'reward': 100,
                'progress': missions.get('social_shares', 0),
                'target': 3
            }
        ]
        
        for mission in active_missions:
            progress_percent = min(100, (mission['progress'] / mission['target']) * 100)
            progress_bar = self.create_progress_bar(progress_percent)
            status = "✅" if mission['progress'] >= mission['target'] else "⏳"
            
            text += f"{status} **{mission['title']}**\n"
            text += f"   {mission['description']}\n"
            text += f"   {progress_bar} {mission['progress']}/{mission['target']}\n"
            text += f"   🎁 Récompense: {mission['reward']} crédits\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🚀 Strategies de mission", callback_data="ref_mission_tips")],
            [InlineKeyboardButton("🏆 Mes accomplissements", callback_data="ref_achievements")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_leaderboard(self, query):
        """Affiche le classement des parrains"""
        leaderboard = self.db.get_referral_leaderboard(limit=10)
        user_id = query.from_user.id
        user_rank = self.db.get_user_referral_rank(user_id)
        
        text = """🏆 **Classement des Parrains**

🥇 Top 10 des meilleurs parrains:

"""
        
        for i, leader in enumerate(leaderboard, 1):
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            
            text += f"{emoji} {leader['username']} - {leader['total_referrals']} filleuls\n"
            text += f"   💰 {leader['total_earnings']} crédits générés\n\n"
        
        text += f"📍 **Votre position:** #{user_rank} sur {self.db.get_total_referrers()}\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Mon objectif", callback_data="ref_set_goal")],
            [InlineKeyboardButton("📊 Statistiques globales", callback_data="ref_global_stats")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def explain_referral_system(self, query):
        """Explique le fonctionnement du système de parrainage"""
        text = """💡 **Comment fonctionne le parrainage?**

🔗 **1. Votre lien unique**
Chaque utilisateur a un lien de parrainage personnel qui suit les inscriptions.

🎁 **2. Récompenses d'inscription**
• Votre filleul: 50 crédits bonus
• Vous: 100 crédits par inscription validée

💰 **3. Commissions récurrentes**
• 10% de tous les achats de vos filleuls
• 5% sur les abonnements Premium
• Bonus sur les renouvellements

🏆 **4. Système de niveaux**
• Bronze (5+ filleuls): +25% bonus
• Argent (15+ filleuls): +50% bonus
• Or (50+ filleuls): +100% bonus
• Diamant (100+ filleuls): +200% bonus

🎯 **5. Missions spéciales**
• Défis mensuels avec récompenses
• Concours saisonniers
• Programmes VIP pour top parrains

💡 **6. Conseils pour réussir**
• Expliquez les vrais avantages
• Aidez vos filleuls à démarrer
• Restez actif et engageant
• Partagez vos succès"""
        
        keyboard = [
            [InlineKeyboardButton("📚 Guide complet", callback_data="ref_complete_guide")],
            [InlineKeyboardButton("🎯 Commencer maintenant", callback_data="ref_start_now")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    def generate_referral_link(self, user_id):
        """Génère un lien de parrainage unique"""
        # Créer un code unique basé sur l'ID utilisateur
        referral_code = hashlib.md5(f"telesuche_{user_id}".encode()).hexdigest()[:8]
        return f"https://t.me/telesuchebot?start=ref_{referral_code}"
    
    def get_tier_benefits(self, tier_level):
        """Retourne les avantages du niveau de parrainage"""
        benefits = {
            0: "• Commissions de base (10%)",
            1: "• Commissions Bronze (+25%)\n• Badge spécial",
            2: "• Commissions Argent (+50%)\n• Support prioritaire",
            3: "• Commissions Or (+100%)\n• Accès VIP\n• Fonctionnalités exclusives",
            4: "• Commissions Diamant (+200%)\n• Co-marketing\n• Revenue sharing"
        }
        return benefits.get(tier_level, benefits[0])
    
    def get_level_emoji(self, level):
        """Retourne l'emoji correspondant au niveau"""
        emojis = {
            0: "🆕",
            1: "🥉",
            2: "🥈", 
            3: "🥇",
            4: "💎"
        }
        return emojis.get(level, "🆕")
    
    def create_progress_bar(self, percentage):
        """Crée une barre de progression"""
        filled = int(percentage / 10)
        empty = 10 - filled
        return "▓" * filled + "░" * empty
    
    async def copy_referral_link(self, query):
        """Simule la copie du lien de parrainage"""
        await query.answer("Lien copié! (simulation - utilisez la fonction de partage)", show_alert=True)
    
    async def show_detailed_stats(self, query):
        """Affiche des statistiques détaillées"""
        user_id = query.from_user.id
        stats = self.db.get_detailed_referral_stats(user_id)
        
        text = f"""📊 **Statistiques Détaillées**

📈 **Performance globale:**
• Total filleuls: {stats['total_referrals']}
• Taux de conversion: {stats['conversion_rate']}%
• Gain moyen/filleul: {stats['avg_earnings_per_referral']} crédits

📅 **Cette semaine:**
• Nouveaux filleuls: {stats['weekly_new']}
• Gains: {stats['weekly_earnings']} crédits
• Activité: {stats['weekly_activity']}%

📅 **Ce mois:**
• Nouveaux filleuls: {stats['monthly_new']}
• Gains: {stats['monthly_earnings']} crédits
• Objectif mensuel: {stats['monthly_progress']}%

🎯 **Projections:**
• Gains prévus ce mois: {stats['projected_monthly']} crédits
• Filleuls potentiels: {stats['potential_referrals']}"""
        
        keyboard = [
            [InlineKeyboardButton("📈 Graphiques", callback_data="ref_charts")],
            [InlineKeyboardButton("🎯 Optimiser", callback_data="ref_optimize")],
            [InlineKeyboardButton("🔙 Retour", callback_data="ref_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def process_referral_signup(self, user_id, referrer_code):
        """Traite l'inscription via un code de parrainage"""
        referrer_id = self.db.get_user_by_referral_code(referrer_code)
        
        if referrer_id and referrer_id != user_id:
            # Enregistrer le parrainage
            self.db.create_referral_relationship(referrer_id, user_id)
            
            # Récompenses
            self.db.add_user_credits(user_id, 50, "Bonus d'inscription via parrainage")
            self.db.add_user_credits(referrer_id, 100, f"Parrainage de l'utilisateur {user_id}")
            
            # Notification au parrain
            return {
                'success': True,
                'referrer_id': referrer_id,
                'bonus_new_user': 50,
                'bonus_referrer': 100
            }
        
        return {'success': False}
