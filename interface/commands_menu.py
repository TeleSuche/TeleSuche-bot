from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from typing import Dict

class CommandsMenu:
    """Gestionnaire du menu des commandes avec internationalisation"""
    
    COMMAND_SECTIONS = {
        'fr': {
            'general': {
                'title': "🧰 <b>Commandes générales</b>",
                'commands': [
                    ("/start", "démarrer le bot"),
                    ("/help", "instructions d’utilisation"),
                    ("/abonnement", "voir les offres"),
                    ("/addcredits", "acheter des crédits"),
                    ("/mycredits", "voir mon solde"),
                    ("/mygroupes", "mes groupes ajoutés"),
                    ("/support", "contacter support"),
                    ("/privacy", "politique de confidentialité")
                ]
            },
            'users': {
                'title': "👥 <b>Gestion utilisateurs (dans les groupes)</b>",
                'commands': [
                    ("/adduser", "ajouter utilisateur"),
                    ("/deleteuser", "supprimer utilisateur"),
                    ("/banuser", "bannir utilisateur"),
                    ("/unbanuser", "débannir utilisateur")
                ]
            },
            'speed': {
                'title': "🚀 <b>Vitesse & abonnements</b>",
                'commands': [
                    ("/addplan", "ajouter un plan de réponse rapide"),
                    ("/deleteplan", "supprimer un plan"),
                    ("/gestionuser", "gérer les abonnés")
                ]
            },
            'shop': {
                'title': "🛒 <b>Vente & paiements</b>",
                'commands': [
                    ("/addstore", "créer une boutique"),
                    ("/additem", "ajouter un article"),
                    ("/createlink", "générer un lien de paiement"),
                    ("/createdon", "créer un lien de don")
                ]
            },
            'support': {
                'title': "🤖 <b>Support bot IA</b>",
                'commands': [
                    ("/createsupport", "créer un bot support"),
                    ("/createsupportAI", "bot support avec IA")
                ]
            },
            'security': {
                'title': "🔐 <b>Sécurité</b>",
                'commands': [
                    ("/pincode", "configurer un code PIN"),
                    ("/toggle2fa", "activer/désactiver 2FA")
                ]
            }
        }
    }

    @classmethod
    async def show_commands_menu(cls, update: Update, context: CallbackContext):
        """Affiche le menu des commandes organisé par sections"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception:
            pass

        lang = context.user_data.get('language', 'fr')
        sections = cls.COMMAND_SECTIONS.get(lang, cls.COMMAND_SECTIONS['fr'])

        text_parts = []
        for section in sections.values():
            text_parts.append(section['title'])
            for cmd, desc in section['commands']:
                text_parts.append(f"{cmd} — {desc}")
            text_parts.append("")  # Ligne vide entre sections

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
        ])

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="\n".join(text_parts),
            parse_mode="HTML",
            reply_markup=keyboard
        )

def setup_commands_handlers(application):
    """Configure les handlers pour le menu des commandes"""
    application.add_handler(
        CallbackQueryHandler(
            CommandsMenu.show_commands_menu,
            pattern="^commands_menu$"
        )
    )