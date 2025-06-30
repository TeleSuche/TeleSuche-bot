from telegram import LabeledPrice
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db

def register_monetization(dispatcher):
    def show_credit_packs(update: Update, context: CallbackContext):
        query = update.callback_query
        keyboard = [
            [
                InlineKeyboardButton("💎 500 crédits (49.99$)", callback_data="buy_pack_500"),
                InlineKeyboardButton("🚀 2000 crédits (149.99$)", callback_data="buy_pack_2000")
            ],
            [
                InlineKeyboardButton("🏆 10000 crédits (499.99$)", callback_data="buy_pack_10000")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text="💰 Packs crédits pour votre communauté:",
            reply_markup=reply_markup
        )

    def handle_pack_purchase(update: Update, context: CallbackContext):
        query = update.callback_query
        pack_size = int(query.data.split("_")[-1])
        
        # Note: L'envoi de factures nécessite un token de fournisseur configuré
        context.bot.send_invoice(
            chat_id=query.from_user.id,
            title=f"Pack {pack_size} crédits",
            description="Crédits partageables avec votre communauté",
            payload=f"credits_{pack_size}",
            provider_token="YOUR_STRIPE_TOKEN",  # À remplacer par votre vrai token
            currency="USD",
            prices=[LabeledPrice("Crédits", pack_size * 100)]  # en cents
        )

    dispatcher.add_handler(CallbackQueryHandler(show_credit_packs, pattern="^credit_packs$"))
    dispatcher.add_handler(CallbackQueryHandler(handle_pack_purchase, pattern="^buy_pack_"))