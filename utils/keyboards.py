from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, List

class KeyboardManager:
    """Gestion centralisée des claviers inline avec internationalisation"""
    
    _LANGUAGES = {
        'fr': '🇫🇷 Français',
        'en': '🇬🇧 English',
        'es': '🇪🇸 Español',
        'de': '🇩🇪 Deutsch',
        'it': '🇮🇹 Italiano',
        'pt': '🇵🇹 Português'
    }

    @classmethod
    def language_selection(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        """Clavier de sélection de langue avec pagination"""
        accept_text = {
            'fr': "✅ J'accepte les conditions",
            'en': "✅ I accept the terms"
        }.get(lang, "✅ Accept")

        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(cls._LANGUAGES['fr'], callback_data='lang_fr'),
                InlineKeyboardButton(cls._LANGUAGES['en'], callback_data='lang_en')
            ],
            [
                InlineKeyboardButton(cls._LANGUAGES['es'], callback_data='lang_es'),
                InlineKeyboardButton(cls._LANGUAGES['de'], callback_data='lang_de')
            ],
            [InlineKeyboardButton(
                "🌍 Plus de langues..." if lang == 'fr' else "🌍 More languages...",
                callback_data='more_langs'
            )]
        ])

    @classmethod
    def terms_accept(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        """Clavier d'acceptation des conditions"""
        button_text = {
            'fr': "✅ J'accepte les conditions",
            'en': "✅ I accept the terms"
        }.get(lang, "✅ Accept")
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, callback_data='accept_terms')]
        ])

    @classmethod
    def main_menu(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        """Menu principal avec support multilingue"""
        translations = {
            'fr': {
                'create': "🛠️ Créer un Bot",
                'channels': "📢 Canaux Officiels",
                'groups': "👥 Groupes Officiels",
                'back': "🔙 Retour",
                'help': "❓ Aide"
            },
            'en': {
                'create': "🛠️ Create Bot",
                'channels': "📢 Official Channels",
                'groups': "👥 Official Groups",
                'back': "🔙 Back",
                'help': "❓ Help"
            }
        }
        t = translations.get(lang, translations['en'])
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t['create'], callback_data='create_bot')],
            [
                InlineKeyboardButton(t['channels'], url="https://t.me/c/2669429903/6"),
                InlineKeyboardButton(t['groups'], url="https://t.me/c/2669429903/7")
            ],
            [
                InlineKeyboardButton(t['back'], callback_data='back'),
                InlineKeyboardButton(t['help'], callback_data='help_command')
            ]
        ])

    @classmethod
    def bot_creation_options(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        """Options de création de bot avec i18n"""
        texts = {
            'fr': {
                'has_token': "✅ J'ai déjà un token",
                'new_token': "🆕 Créer un nouveau token",
                'back': "🔙 Retour"
            },
            'en': {
                'has_token': "✅ I already have a token",
                'new_token': "🆕 Create new token",
                'back': "🔙 Back"
            }
        }
        t = texts.get(lang, texts['en'])
        
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t['has_token'], callback_data='has_token_yes')],
            [InlineKeyboardButton(t['new_token'], callback_data='has_token_no')],
            [InlineKeyboardButton(t['back'], callback_data='back')]
        ])

# Fonctions legacy pour compatibilité
def language_selection_keyboard():
    return KeyboardManager.language_selection()

def terms_accept_keyboard():
    return KeyboardManager.terms_accept()

def main_menu_keyboard():
    return KeyboardManager.main_menu()

def bot_creation_options():
    return KeyboardManager.bot_creation_options()