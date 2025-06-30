from telegram import Update
from telegram.ext import CallbackContext, CommandHandler
from utils.memory_full import db

REFERRAL_CREDITS = 35

def register_referral_system(dispatcher):
    def generate_invite(update: Update, context: CallbackContext):
        user_id = update.message.from_user.id
        invite_code = f"ref_{user_id}_{db.generate_token()}"
        db.save_invite_code(user_id, invite_code)
        
        update.message.reply_text(
            f"🎁 Partagez ce lien pour gagner {REFERRAL_CREDITS} crédits par ami:\n"
            f"t.me/{context.bot.username}?start={invite_code}"
        )

    def show_referrals(update: Update, context: CallbackContext):
        stats = db.get_referral_stats(update.message.from_user.id)
        update.message.reply_text(
            f"📊 Vos parrainages:\n"
            f"👥 Personnes invitées: {stats['count']}\n"
            f"🎁 Crédits gagnés: {stats['credits']}"
        )

    dispatcher.add_handler(CommandHandler("invite", generate_invite))
    dispatcher.add_handler(CommandHandler("myrefs", show_referrals))