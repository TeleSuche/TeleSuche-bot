from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from typing import Tuple, Dict, Literal

class ProductPreview:
    """Génère des aperçus de produits avec interfaces adaptées"""
    
    @staticmethod
    def _build_base_text(data: Dict) -> str:
        """Construit le texte de base commun aux deux vues"""
        return (
            f"📦 <b>{data['name']}</b>\n"
            f"📄 {data['description']}\n"
            f"💰 Prix : {data['price']} {data['currency']}\n"
            f"🗓️ Offre valable jusqu'au : <i>{data.get('expiry', 'indéfini')}</i>"
        )

    @classmethod
    def build_user_view(cls, data: Dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Aperçu pour les utilisateurs normaux"""
        text = cls._build_base_text(data)
        
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛒 Acheter", callback_data="buy_now"),
                InlineKeyboardButton("💡 En savoir plus", callback_data="info_link")
            ],
            [InlineKeyboardButton("↗️ Partager", switch_inline_query="")]
        ])
        
        return text, markup

    @classmethod
    def build_creator_view(cls, data: Dict) -> Tuple[str, InlineKeyboardMarkup]:
        """Aperçu avec options de gestion pour le créateur"""
        text = cls._build_base_text(data)
        
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛒 Acheter", callback_data="buy_now"),
                InlineKeyboardButton("💡 En savoir plus", callback_data="info_link")
            ],
            [InlineKeyboardButton("↗️ Partager", switch_inline_query="")],
            [
                InlineKeyboardButton("⚙️ Modifier", callback_data="edit_link"),
                InlineKeyboardButton("🔁 Générer un lien", callback_data="generate_link")
            ]
        ])
        
        return text, markup

    @classmethod
    async def send_preview(
        cls,
        update_or_context,
        data: Dict,
        view_type: Literal['user', 'creator'] = 'user'
    ):
        """
        Envoie l'aperçu du produit
        Args:
            update_or_context: Update ou CallbackContext
            data: Données du produit (doit contenir 'photo_file_id')
            view_type: 'user' ou 'creator'
        """
        if view_type == 'creator':
            text, markup = cls.build_creator_view(data)
        else:
            text, markup = cls.build_user_view(data)

        # Gère à la fois les messages initiaux et les éditions
        if hasattr(update_or_context, 'message'):
            await update_or_context.message.reply_photo(
                photo=data['photo_file_id'],
                caption=text,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await update_or_context.bot.send_photo(
                chat_id=update_or_context.effective_chat.id,
                photo=data['photo_file_id'],
                caption=text,
                parse_mode="HTML",
                reply_markup=markup
            )