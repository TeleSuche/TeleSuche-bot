import logging
logger = logging.getLogger(__name__)
# translations.py - Système complet de gestion des traductions

from typing import Dict, Any, Optional
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TranslationManager:
    """Gestionnaire avancé des traductions avec support multi-sources"""
    
    def __init__(self, locale_dir: str = "i18n/locales"):
        self.locale_dir = Path(locale_dir)
        self.translations: Dict[str, Dict[str, str]] = {}
        self.default_language = "fr"
        self._load_builtin_translations()
        self.load_all_translations()

    def _load_builtin_translations(self):
        """Charge les traductions intégrées"""
        self.translations = {
            'fr': {
                'welcome': "👋 Bienvenue dans TeleSucheBot!\n\nVeuillez choisir votre langue préférée :",
                'terms': "[📜 Conditions d'utilisation](https://votre-lien.com/terms)",
                'accept_button': "✅ J'accepte les conditions",
                'setup_message': (
                    "⚙️ <b>Configuration du Bot</b>\n\n"
                    "Choisissez une option :\n"
                    "1. /setup_basics - Paramètres de base\n"
                    "2. /setup_features - Fonctionnalités\n"
                    "3. /setup_payments - Paiements\n"
                    "4. /help - Aide"
                ),
                'auth_success': (
                    "🎉 <b>Authentification réussie !</b>\n\n"
                    "🚀 <b>Fonctionnalités disponibles :</b>\n"
                    "Ici, vous pouvez utiliser votre bot et tout gérer. Besoin d'aide ?\n"
                    '<a href="https://aide.telegrambot.com/guide-utilisateur">Guide d\'utilisation</a>\n'
                    "-----\n"
                ),
                'setup_basics': "⚙️ Paramètres de base du bot",
                'setup_features': "✨ Configuration des fonctionnalités",
                'setup_payments': "💳 Paramètres de paiement",
                'back_button': "🔙 Retour",
                'setup_complete': "✅ Configuration terminée avec succès",
                'setup_error': "❌ Erreur lors de la configuration",
                'start_welcome': (
                    "🤖 <b>Bienvenue sur {bot_name}</b> !\n\n"
                    "🧰 <b>Fonctionnalités activées</b> :\n"
                    "🔍 Recherche intelligente\n"
                    "💬 Réponses automatisées (IA)\n"
                    "📊 Analytics temps réel\n"
                    "🛠️ Gestion des abonnements\n"
                    "👥 Gestion des groupes\n\n"
                    "🌟 <b>Prochaines étapes</b> : Utilisez /setup ou le bouton ci-dessous"
                )
            },
            'en': {
                'welcome': "👋 Welcome to TeleSucheBot!\n\nPlease choose your preferred language:",
                'terms': "[📜 Terms of use](https://your-link.com/terms)",
                'accept_button': "✅ I accept the terms",
                'setup_message': (
                    "⚙️ <b>Bot Configuration</b>\n\n"
                    "Choose an option:\n"
                    "1. /setup_basics - Basic settings\n"
                    "2. /setup_features - Features\n"
                    "3. /setup_payments - Payments\n"
                    "4. /help - Help"
                ),
                'auth_success': (
                    "🎉 <b>Authentication successful!</b>\n\n"
                    "🚀 <b>Available features:</b>\n"
                    "Here you can use your bot and manage everything. Need help?\n"
                    '<a href="https://help.telegrambot.com/user-guide">User Guide</a>\n'
                    "-----\n"
                ),
                'setup_basics': "⚙️ Bot basic settings",
                'setup_features': "✨ Features configuration",
                'setup_payments': "💳 Payment settings",
                'back_button': "🔙 Back",
                'setup_complete': "✅ Setup completed successfully",
                'setup_error': "❌ Error during setup",
                'start_welcome': (
                    "🤖 <b>Welcome to {bot_name}</b> !\n\n"
                    "🧰 <b>Enabled features:</b> :\n"
                    "🔍 Smart search\n"
                    "💬 Automated replies (AI)\n"
                    "📊 Real-time analytics\n"
                    "🛠️ Subscription management\n"
                    "👥 Group management\n\n"
                    "🌟 <b>Next steps</b> : Use /setup or the button below"
                )
            }
        }

    def load_all_translations(self):
        """Charge les traductions externes depuis le dossier locales"""
        try:
            if not self.locale_dir.exists():
                self.locale_dir.mkdir(parents=True)
                logger.info(f"Created locale directory: {self.locale_dir}")

            for lang_file in self.locale_dir.glob("*.json"):
                lang = lang_file.stem
                with open(lang_file, 'r', encoding='utf-8') as f:
                    if lang not in self.translations:
                        self.translations[lang] = {}
                    self.translations[lang].update(json.load(f))
        except Exception as e:
            logger.error(f"Error loading translations: {e}")

    def get(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Récupère une traduction avec formatage
        
        Args:
            key: Clé de traduction
            lang: Langue cible (optionnelle)
            kwargs: Variables de remplacement
            
        Returns:
            str: Texte traduit formaté
        """
        lang = lang or self.default_language
        try:
            text = self.translations.get(lang, {}).get(
                key, 
                self.translations.get(self.default_language, {}).get(key, key)
            )
            return text.format(**kwargs) if kwargs else text
        except Exception as e:
            logger.error(f"Translation error for key '{key}': {e}")
            return key

    def get_available_languages(self) -> list:
        """Liste des langues disponibles"""
        return list(self.translations.keys())

# Instance globale
translator = TranslationManager()

# Fonctions d'interface pour compatibilité
def t(key: str, lang: str = None, **kwargs) -> str:
    """Alias pour translator.get (compatibilité legacy)"""
    return translator.get(key, lang, **kwargs)

def get_text(key: str, lang: str = None, **kwargs) -> str:
    """Alias standard pour récupérer les traductions"""
    return translator.get(key, lang, **kwargs)

# Alias pour l'import dans user_administrator.py
TranslationManager = TranslationManager