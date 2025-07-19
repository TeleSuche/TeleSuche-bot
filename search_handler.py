import logging
logger = logging.getLogger(__name__)
from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackQueryHandler, CallbackContext
import logging
from utils.memory_full import db
from extensions.handlers.search_engine import SearchEngine

logger = logging.getLogger(__name__)

def register_search_handler(application):
    SearchEngine.register(application)

    async def handle_natural_query(update: Update, context: CallbackContext):
        message = update.message
        user_id = message.from_user.id
        if not db.has_credits(user_id):
            await message.reply_text("❌ Crédits insuffisants. Utilisez /addcredits")
            return

        query = message.text.lower().replace("je cherche", "").strip()
        if not query:
            await message.reply_text("❌ Veuillez spécifier votre recherche après 'je cherche'")
            return

        await context.bot.process_update(Update(
            update_id=update.update_id,
            message=message,
            message_id=message.message_id,
            chat=message.chat,
            from_user=message.from_user,
            text=f"/search {query}"
        ))

    async def handle_download(update: Update, context: CallbackContext):
        query = update.callback_query
        try:
            file_id = query.data.split('_')[1]
            file_data = db.get_file_by_id(file_id)

            if not file_data:
                await query.answer("❌ Fichier introuvable", show_alert=True)
                return

            # Vérifie si groupe autorisé pour télécharger ce fichier
            if not db.is_search_group(query.message.chat.id):
                await query.answer("🚫 Ce groupe n'est pas autorisé à effectuer des téléchargements", show_alert=True)
                return

            # Envoi du fichier selon le type
            if file_data['file_type'] == 'document':
                await query.message.reply_document(file_data['file_id'])
            elif file_data['file_type'] == 'photo':
                await query.message.reply_photo(file_data['file_id'])
            elif file_data['file_type'] == 'video':
                await query.message.reply_video(file_data['file_id'])
            elif file_data['file_type'] == 'audio':
                await query.message.reply_audio(file_data['file_id'])

            await query.answer()

            db.save_download_history(
                query.from_user.id,
                query.message.chat.id,
                file_data['title'],
                file_data['file_id']
            )

        except Exception as e:
            logger.error(f"Download error: {e}")
            await query.answer("❌ Erreur lors du téléchargement", show_alert=True)

    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)je cherche'),
        handle_natural_query
    ))
    application.add_handler(CallbackQueryHandler(
        handle_download,
        pattern='^download_'
    ))