from telegram import LabeledPrice
telegram_gemini_5/handlers/monetization.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import (CallbackContext, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters) from utils.memory_full import db

SPEED_COSTS = {"standard": 0, "fast": 1, "instant": 5} PRIVACY_COSTS = {"public": 0, "private": 3}

--- MENUS ---

async def show_group_menu(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass buttons = [ [InlineKeyboardButton("🎛 Monétisation", callback_data="menu_monetization")], [InlineKeyboardButton("💳 Crédits", callback_data="add_credits")] ] await update.effective_message.reply_text("📋 Menu de configuration du groupe :", reply_markup=InlineKeyboardMarkup(buttons))

async def show_monetization_menu(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass buttons = [ [InlineKeyboardButton("⚙️ Vitesse", callback_data="menu_speed"), InlineKeyboardButton("🔐 Confidentialité", callback_data="menu_privacy")], [InlineKeyboardButton("📊 Voir tarifs", callback_data="menu_pricing")], [InlineKeyboardButton("💳 Acheter crédits", callback_data="menu_buycredits")], [InlineKeyboardButton("⬅️ Retour", callback_data="menu_back_groupmenu")] ] await update.effective_message.reply_text("🛠 Menu de configuration monétisation :", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_menu_callback(update: Update, context: CallbackContext): query = update.callback_query match query.data: case "menu_speed": await set_speed(update, context) case "menu_privacy": await set_privacy(update, context) case "menu_pricing": await show_pricing(update, context) case "menu_buycredits": await show_credit_packs(update, context) case "menu_monetization": await show_monetization_menu(update, context) case "menu_back_groupmenu": await show_group_menu(update, context) await query.answer()

--- PARAMÈTRES ---

async def set_speed(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass buttons = [ [InlineKeyboardButton("🐢 Standard (0)", callback_data="speed_standard")], [InlineKeyboardButton("⚡ Rapide (1)", callback_data="speed_fast")], [InlineKeyboardButton("🚀 Instantané (5)", callback_data="speed_instant")], [InlineKeyboardButton("⬅️ Retour", callback_data="menu_monetization")] ] await update.effective_message.reply_text("⚙️ Choisissez la vitesse :", reply_markup=InlineKeyboardMarkup(buttons))

async def set_privacy(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass buttons = [ [InlineKeyboardButton("🌐 Public (0)", callback_data="privacy_public")], [InlineKeyboardButton("🔒 Privé (3)", callback_data="privacy_private")], [InlineKeyboardButton("⬅️ Retour", callback_data="menu_monetization")] ] await update.effective_message.reply_text("🔐 Choisissez la confidentialité :", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_speed_choice(update: Update, context: CallbackContext): query = update.callback_query speed = query.data.split('_')[1] db.set_group_param(query.message.chat.id, "speed", speed) await query.edit_message_text(f"✅ Vitesse réglée : {speed}") await query.answer()

async def handle_privacy_choice(update: Update, context: CallbackContext): query = update.callback_query privacy = query.data.split('_')[1] db.set_group_param(query.message.chat.id, "privacy", privacy) await query.edit_message_text(f"🔐 Confidentialité : {privacy}") await query.answer()

--- RECHERCHE PAYANTE ---

async def handle_paid_search(update: Update, context: CallbackContext): chat_id = update.message.chat.id user_id = update.message.from_user.id speed = db.get_group_param(chat_id, "speed") or "standard" privacy = db.get_group_param(chat_id, "privacy") or "public" cost = SPEED_COSTS[speed] + PRIVACY_COSTS[privacy] owner_id = db.get_group_owner(chat_id) if not db.has_admin_credits(owner_id, cost): await update.message.reply_text("❌ Crédits insuffisants.") return db.deduct_admin_credit(owner_id, cost) await update.message.reply_text(f"🔍 Requête traitée ({speed}, {privacy}) pour {cost} crédits")

--- TARIFS ---

async def show_pricing(update: Update, context: CallbackContext): text = ( "📊 <b>Tarifs actuels</b>\n\n" "<b>Vitesse</b>\n🐢 Standard: 0\n⚡ Rapide: 1\n🚀 Instantané: 5\n\n" "<b>Confidentialité</b>\n🌐 Public: 0\n🔒 Privé: 3" ) await update.effective_message.reply_text(text, parse_mode="HTML")

--- CRÉDITS ---

async def show_credit_packs(update: Update, context: CallbackContext): if update.callback_query: try: await update.callback_query.message.delete() except: pass buttons = [ [InlineKeyboardButton("Pack 500", callback_data="buy_pack_500")], [InlineKeyboardButton("Pack 1000", callback_data="buy_pack_1000")], [InlineKeyboardButton("⬅️ Retour", callback_data="menu_monetization")] ] await update.effective_message.reply_text("🛒 Choisissez un pack :", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_buy_pack(update: Update, context: CallbackContext): pack = update.callback_query.data.split('')[-1] prices = {"500": LabeledPrice("Pack 500", 50000), "1000": LabeledPrice("Pack 1000", 90000)} await context.bot.send_invoice( chat_id=update.effective_chat.id, title="Achat de crédits", description=f"{pack} crédits pour vos recherches", payload=f"credits{pack}", provider_token="PROVIDER_TOKEN", currency="USD", prices=[prices[pack]] ) await update.callback_query.answer()

async def precheckout_callback(update: Update, context: CallbackContext): await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context: CallbackContext): amount = int(update.message.successful_payment.invoice_payload.split('_')[-1]) db.add_admin_credits(update.message.from_user.id, amount) await update.message.reply_text(f"✅ {amount} crédits ajoutés")

--- ENREGISTREMENT ---

def setup(application): application.add_handler(CommandHandler("groupmenu", show_group_menu)) application.add_handler(CommandHandler("premiumsearch", handle_paid_search)) application.add_handler(CommandHandler("pricing", show_pricing)) application.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_")) application.add_handler(CallbackQueryHandler(handle_speed_choice, pattern="^speed_")) application.add_handler(CallbackQueryHandler(handle_privacy_choice, pattern="^privacy_")) application.add_handler(CallbackQueryHandler(handle_buy_pack, pattern="^buy_pack_")) application.add_handler(PreCheckoutQueryHandler(precheckout_callback)) application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
