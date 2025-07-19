# Fichier: handlers/official_links.py

from telegram import Update
from telegram.ext import CallbackContext, CallbackQueryHandler

async def show_official_channels(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    lang = memory_storage.get_user_lang(query.from_user.id)
    
    if lang == 'fr':
        text = (
            "🌐 Rejoignez nos canaux officiels :\n\n"
            "- [Canal principal](https://t.me/votre_canal_principal)\n"
            "- [Annonces](https://t.me/votre_canal_annonces)\n"
            "- [Promotions](https://t.me/votre_canal_promos)"
        )
    else:
        text = (
            "🌐 Join our official channels:\n\n"
            "- [Main channel](https://t.me/your_main_channel)\n"
            "- [Announcements](https://t.me/your_announcements)\n"
            "- [Promotions](https://t.me/your_promotions)"
        )
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def show_official_groups(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    lang = memory_storage.get_user_lang(query.from_user.id)
    
    if lang == 'fr':
        text = (
            "👥 Rejoignez nos groupes officiels :\n\n"
            "- [Groupe communautaire](https://t.me/votre_groupe_communaute)\n"
            "- [Support technique](https://t.me/votre_groupe_support)\n"
            "- [Développeurs](https://t.me/votre_groupe_devs)"
        )
    else:
        text = (
            "👥 Join our official groups:\n\n"
            "- [Community group](https://t.me/your_community_group)\n"
            "- [Technical support](https://t.me/your_support_group)\n"
            "- [Developers](https://t.me/your_devs_group)"
        )
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

def setup(dispatcher):
    dispatcher.add_handler(CallbackQueryHandler(show_official_channels, pattern='^official_channels$'))
    dispatcher.add_handler(CallbackQueryHandler(show_official_groups, pattern='^official_groups$'))