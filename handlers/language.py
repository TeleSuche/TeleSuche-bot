# handlers/language.py

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler
from utils.memory_full import db
from utils.keyboards import language_selection_keyboard, terms_accept_keyboard, LANGUAGES


async def start_language_selection(update: Update, context: CallbackContext):
    if update.message:
        await update.message.reply_text(
            "👋 Bienvenue dans TeleSucheBot!\nVeuillez choisir votre langue :",
            reply_markup=language_selection_keyboard()
        )
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "👋 Bienvenue dans TeleSucheBot!\nVeuillez choisir votre langue :",
            reply_markup=language_selection_keyboard()
        )


async def handle_language_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'more_langs':
        await query.edit_message_text("D'autres langues seront ajoutées prochainement !")
        return

    lang_code = query.data.split('_')[1]
    user_id = query.from_user.id
    db.set_user_language(user_id, lang_code)  # ✅ Appel corrigé

    lang_name = LANGUAGES.get(lang_code, lang_code.upper())
    terms_text = (
        f"🌐 Langue sélectionnée: {lang_name}\n\n"
        "📜 Veuillez accepter nos conditions d'utilisation pour continuer :\n"
        "[Lire les conditions](https://votre-lien.com/terms)"
    )

    await query.edit_message_text(
        terms_text,
        reply_markup=terms_accept_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


def setup(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(handle_language_selection, pattern='^lang_'))
    dispatcher.add_handler(CallbackQueryHandler(handle_language_selection, pattern='^more_langs$'))
