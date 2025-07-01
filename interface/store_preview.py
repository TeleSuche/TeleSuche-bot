import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CallbackContext
from typing import Dict, Optional, Union
from dataclasses import dataclass
from utils.memory_full import db

logger = logging.getLogger(__name__)

@dataclass
class StoreItem:
    name: str
    description: str
    price: float
    currency: str
    photo_id: str
    delivery_mode: str
    expiry_date: Optional[str] = None

class StorePreview:
    """Gestionnaire d'aperçu de boutique avec template configurable"""

    @staticmethod
    def _build_caption(item: StoreItem) -> str:
        """Construit la légende formatée pour l'article"""
        return (
            f"🛍️ <b>{item.name}</b>\n\n"
            f"{item.description}\n\n"
            f"💰 Prix : {item.price} {item.currency}\n"
            f"🚚 Mode de livraison : {'En ligne' if item.delivery_mode == 'online' else 'À la livraison'}\n"
            f"🗓️ Offre valable jusqu'au : {item.expiry_date or 'Non spécifié'}"
        )

    @staticmethod
    def _build_keyboard(item_name: str) -> InlineKeyboardMarkup:
        """Construit le clavier interactif"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🛒 Acheter", callback_data="buy_now"),
                InlineKeyboardButton("ℹ️ Détails", callback_data="store_info")
            ],
            [InlineKeyboardButton("↗️ Partager", switch_inline_query=item_name)],
            [
                InlineKeyboardButton("⚙️ Modifier", callback_data="store_edit"),
                InlineKeyboardButton("🔗 Lien", callback_data="generate_link")
            ]
        ])

    @classmethod
    async def send(
        cls,
        update_or_context: Union[Update, CallbackContext],
        user_id: int,
        edit_message: bool = False
    ) -> None:
        """Envoie ou édite l'aperçu de la boutique"""
        try:
            data = db.get_store_data(user_id)
            if not data:
                error_msg = "❌ Aucun produit configuré. Utilisez /addstore pour créer un produit."
                if hasattr(update_or_context, 'message'):
                    await update_or_context.message.reply_text(error_msg)
                else:
                    await update_or_context.bot.send_message(user_id, error_msg)
                return

            item = StoreItem(
                name=data.get("name", "Sans nom"),
                description=data.get("description", "Aucune description"),
                price=data.get("price", 0.0),
                currency=data.get("currency", "€"),
                photo_id=data.get("photo", ""),
                delivery_mode=data.get("delivery_mode", "online"),
                expiry_date=data.get("expiry_date")
            )

            caption = cls._build_caption(item)
            keyboard = cls._build_keyboard(item.name)

            if edit_message and hasattr(update_or_context, 'callback_query'):
                query = update_or_context.callback_query
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=item.photo_id,
                        caption=caption,
                        parse_mode="HTML"
                    ),
                    reply_markup=keyboard
                )
            else:
                if hasattr(update_or_context, 'message'):
                    await update_or_context.message.reply_photo(
                        photo=item.photo_id,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                else:
                    await update_or_context.bot.send_photo(
                        chat_id=user_id,
                        photo=item.photo_id,
                        caption=caption,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    
        except Exception as e:
            logger.error(f"Erreur StorePreview: {e}")
            error_msg = "⚠️ Erreur lors de l'affichage du produit. Veuillez réessayer."
            if hasattr(update_or_context, 'message'):
                await update_or_context.message.reply_text(error_msg)
            else:
                await update_or_context.bot.send_message(user_id, error_msg)

def register_store_preview(application):
    """Configure les handlers liés à la prévisualisation"""
    application.add_handler(CallbackQueryHandler(
        lambda u, c: StorePreview.send(u, u.effective_user.id, edit_message=True),
        pattern="^store_edit_preview$"
    ))