from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db

def get_referral_markup(user_id: int) -> InlineKeyboardMarkup:
    markup = []
    ref_code = db.get_ref_code(user_id)
    
    markup.append([
        InlineKeyboardButton(
            "📤 Partager", 
            switch_inline_query=f"Rejoins ce bot avec mon lien : https://t.me/YourBot?start=ref_{ref_code}"
        )
    ])
    
    markup.append([
        InlineKeyboardButton(
            "💼 Mes gains", 
            callback_data="my_earnings"
        )
    ])
    
    return InlineKeyboardMarkup(markup)

def register(application):
    def show_earnings(update, context: CallbackContext):
        query = update.callback_query
        user_id = query.from_user.id
        earnings = db.get_user_earnings(user_id)
        
        text = (
            f"💰 <b>Vos gains de parrainage</b>\n\n"
            f"• Personnes invitées: {earnings['referred_count']}\n"
            f"• Crédits gagnés: {earnings['credits_earned']}\n"
            f"• Gains financiers: ${earnings['cash_earned']:.2f}\n\n"
            "🔹 Ces gains sont disponibles dans votre portefeuille administrateur"
        )
        
        query.message.reply_text(text, parse_mode="HTML")
        query.answer()
    
    application.add_handler(CallbackQueryHandler(show_earnings, pattern="^my_earnings$"))