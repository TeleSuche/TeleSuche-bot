import logging
logger = logging.getLogger(__name__)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from typing import List, Tuple

# Liste complète des devises avec emoji drapeau
CURRENCIES: List[Tuple[str, str]] = [
    ("USD", "🇺🇸 Dollar US"), ("EUR", "🇪🇺 Euro"), ("CDF", "🇨🇩 Franc Congolais"),
    ("XOF", "🇸🇳 Franc CFA Ouest"), ("XAF", "🇨🇲 Franc CFA Central"),
    ("GBP", "🇬🇧 Livre Sterling"), ("JPY", "🇯🇵 Yen Japonais"), ("CNY", "🇨🇳 Yuan Chinois"),
    ("INR", "🇮🇳 Roupie Indienne"), ("BRL", "🇧🇷 Real Brésilien"), ("CAD", "🇨🇦 Dollar Canadien"),
    ("AUD", "🇦🇺 Dollar Australien"), ("AED", "🇦🇪 Dirham UAE"), ("ZAR", "🇿🇦 Rand Sud-Africain"),
    ("CHF", "🇨🇭 Franc Suisse"), ("RUB", "🇷🇺 Rouble Russe"), ("KRW", "🇰🇷 Won Sud-Coréen"),
    ("TRY", "🇹🇷 Livre Turque"), ("MXN", "🇲🇽 Peso Mexicain"), ("SEK", "🇸🇪 Couronne Suédoise"),
    ("NOK", "🇳🇴 Couronne Norvégienne"), ("DKK", "🇩🇰 Couronne Danoise"),
    ("PLN", "🇵🇱 Zloty Polonais"), ("TND", "🇹🇳 Dinar Tunisien"), ("EGP", "🇪🇬 Livre Égyptienne"),
    ("MAD", "🇲🇦 Dirham Marocain"), ("GHS", "🇬🇭 Cedi Ghanéen"), ("NGN", "🇳🇬 Naira Nigérian"),
    ("KES", "🇰🇪 Shilling Kényan"), ("TZS", "🇹🇿 Shilling Tanzanien")
]

ITEMS_PER_PAGE = 6

class CurrencySelector:
    """Gestionnaire de sélection de devise avec pagination"""

    @staticmethod
    def get_currency_markup(page: int = 0) -> InlineKeyboardMarkup:
        """Génère le clavier des devises avec pagination"""
        start = page * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        current_currencies = CURRENCIES[start:end]

        buttons = []
        for code, label in current_currencies:
            buttons.append([InlineKeyboardButton(label, callback_data=f"currency_{code}")])

        # Boutons de navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Précédent", callback_data=f"currency_page_{page - 1}"))
        if end < len(CURRENCIES):
            nav_buttons.append(InlineKeyboardButton("➡️ Suivant", callback_data=f"currency_page_{page + 1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        # Bouton de retour
        buttons.append([InlineKeyboardButton("🔙 Retour", callback_data="back_price")])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    async def handle_currency_page(update: Update, context: CallbackContext) -> None:
        """Gère le changement de page des devises"""
        query = update.callback_query
        await query.answer()

        page = int(query.data.split("_")[-1])
        
        try:
            await query.edit_message_reply_markup(
                reply_markup=CurrencySelector.get_currency_markup(page)
            )
        except Exception as e:
            logger.error(f"Error updating currency page: {e}")

def setup_currency_handlers(application):
    """Configure les handlers pour la sélection de devise"""
    application.add_handler(
        CallbackQueryHandler(
            CurrencySelector.handle_currency_page,
            pattern=r"^currency_page_\d+$"  # Regex pour mieux cibler le pattern
        )
    )