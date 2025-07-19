
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.memory_full import db

class KeyboardManager:
    """Gestion centralisée des claviers inline avec internationalisation"""

    LANGUAGES = {
        'fr': '🇫🇷 Français',
        'en': '🇬🇧 English',
        'es': '🇪🇸 Español',
        'de': '🇩🇪 Deutsch',
        'it': '🇮🇹 Italiano',
        'pt': '🇵🇹 Português',
        'ru': '🇷🇺 Русский'
    }

    @classmethod
    def language_selection(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(cls.LANGUAGES['fr'], callback_data='lang_fr'),
                InlineKeyboardButton(cls.LANGUAGES['en'], callback_data='lang_en')
            ],
            [
                InlineKeyboardButton(cls.LANGUAGES['es'], callback_data='lang_es'),
                InlineKeyboardButton(cls.LANGUAGES['de'], callback_data='lang_de')
            ],
            [
                InlineKeyboardButton(cls.LANGUAGES['ru'], callback_data='lang_ru')
            ],
            [InlineKeyboardButton(
                "🌍 Plus de langues..." if lang == 'fr' else "🌍 More languages...",
                callback_data='morelangs'
            )]
        ])

    @classmethod
    def change_language(cls, update, context):
        user_id = update.effective_user.id
        lang = db.get_user_language(user_id) or 'fr'
        text = "🌍 Choisissez votre langue :" if lang == 'fr' else "🌍 Choose your language:"
        keyboard = cls.language_selection(lang)
        update.message.reply_text(text, reply_markup=keyboard)

    @classmethod
    def terms_accept(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        button_text = {
            'fr': "✅ J'accepte les conditions",
            'en': "✅ I accept the terms",
            'es': "✅ Acepto los términos",
            'de': "✅ Ich akzeptiere die Bedingungen",
            'ru': "✅ Я принимаю условия"
        }.get(lang, "✅ Accept")

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(button_text, callback_data='accept_terms')]
        ])

    @classmethod
    def main_menu(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        translations = {
            'fr': {
                'create': "⚙️ Cloner votre bot",
                'community': "🤝 Communauté",
                'services': "🛠️ Services",
                'help': "🆘 Aide"
            },
            'en': {
                'create': "⚙️ Clone your bot",
                'community': "🤝 Community",
                'services': "🛠️ Services",
                'help': "🆘 Help"
            },
            'es': {
                'create': "⚙️ Clonar tu bot",
                'community': "🤝 Comunidad",
                'services': "🛠️ Servicios",
                'help': "🆘 Ayuda"
            },
            'de': {
                'create': "⚙️ Bot klonen",
                'community': "🤝 Gemeinschaft",
                'services': "🛠️ Dienstleistungen",
                'help': "🆘 Hilfe"
            },
            'ru': {
                'create': "⚙️ Клонировать бота",
                'community': "🤝 Сообщество",
                'services': "🛠️ Сервисы",
                'help': "🆘 Помощь"
            }
        }
        t = translations.get(lang, translations['en'])

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t['create'], callback_data='createbot')],
            [InlineKeyboardButton(t['community'], callback_data='join_us')],
            [
                InlineKeyboardButton(t['services'], callback_data='services_menu'),
                InlineKeyboardButton(t['help'], callback_data='help_command')
            ]
        ])

    @classmethod
    def get_join_us_keyboard(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
        translations = {
            'fr': {
                'channels': "📢 Canaux Officiels",
                'groups': "👥 Groupes Officiels",
                'back': "🔙 Retour"
            },
            'en': {
                'channels': "📢 Official Channels",
                'groups': "👥 Official Groups",
                'back': "🔙 Back"
            },
            'es': {
                'channels': "📢 Canales Oficiales",
                'groups': "👥 Grupos Oficiales",
                'back': "🔙 Volver"
            },
            'de': {
                'channels': "📢 Offizielle Kanäle",
                'groups': "👥 Offizielle Gruppen",
                'back': "🔙 Zurück"
            },
            'ru': {
                'channels': "📢 Официальные каналы",
                'groups': "👥 Официальные группы",
                'back': "🔙 Назад"
            }
        }
        t = translations.get(lang, translations['en'])

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t['channels'], callback_data='official_channels')],
            [InlineKeyboardButton(t['groups'], callback_data='official_groups')],
            [InlineKeyboardButton(t['back'], callback_data='back_to_main')]
        ])

    @classmethod
    def bot_creation_options(cls, lang: str = 'fr') -> InlineKeyboardMarkup:
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
            },
            'es': {
                'has_token': "✅ Ya tengo un token",
                'new_token': "🆕 Crear nuevo token",
                'back': "🔙 Volver"
            },
            'de': {
                'has_token': "✅ Ich habe bereits ein Token",
                'new_token': "🆕 Neues Token erstellen",
                'back': "🔙 Zurück"
            },
            'ru': {
                'has_token': "✅ У меня уже есть токен",
                'new_token': "🆕 Создать новый токен",
                'back': "🔙 Назад"
            }
        }
        t = texts.get(lang, texts['en'])

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(t['has_token'], callback_data='hastokenyes')],
            [InlineKeyboardButton(t['new_token'], callback_data='hastokenno')],
            [InlineKeyboardButton(t['back'], callback_data='back')]
        ])

def language_selection_keyboard():
    return KeyboardManager.language_selection()

def terms_accept_keyboard(lang: str = 'fr'):
    return KeyboardManager.terms_accept(lang)

def main_menu_keyboard(lang: str = 'fr'):
    return KeyboardManager.main_menu(lang)

def bot_creation_options(lang: str = 'fr'):
    return KeyboardManager.bot_creation_options(lang)

LANGUAGES = KeyboardManager.LANGUAGES
