telegram_gemini_5/handlers/user_plan_info.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackContext from utils.memory_full import db from extensions.handlers.subscriptions import get_plan_limits

async def show_plan_info(update: Update, context: CallbackContext): user_id = update.effective_user.id plan = db.get("user_plans", {}).get(user_id, "sub_basic") limits = get_plan_limits(plan)

bots = db.get_user_bots(user_id)
bot_count = len(bots)
group_count = sum(len(bot.get("groups", [])) for bot in bots)
channel_count = sum(len(bot.get("channels", [])) for bot in bots)

text = (
    f"📦 <b>Votre abonnement</b>\n"
    f"Plan actif : <code>{plan}</code>\n\n"
    f"🤖 Bots : {bot_count}/{limits['bots']}\n"
    f"👥 Groupes : {group_count}/{limits['groups']}\n"
    f"📣 Canaux : {channel_count}/{limits['channels']}\n"
)

buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("🆙 Passer à un plan supérieur", callback_data="upgrade_plan")]
])

await update.message.reply_text(text, parse_mode="HTML", reply_markup=buttons)

--- SETUP ---

def setup(application: Application): application.add_handler(CommandHandler("planinfo", show_plan_info))