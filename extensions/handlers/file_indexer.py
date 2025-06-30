import logging
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, MessageHandler, Filters, CallbackQueryHandler import logging from utils.memory_full import db

logger = logging.getLogger(name)

class FileIndexer: FILE_TYPES = { 'document': {'emoji': '📄', 'reward': 10}, 'video': {'emoji': '🎬', 'reward': 20}, 'photo': {'emoji': '🖼️', 'reward': 3}, 'audio': {'emoji': '🎧', 'reward': 5} }

@staticmethod
def register(application):
    def handle_file(update: Update, context: CallbackContext):
        message = update.message
        if not db.is_search_group(message.chat.id):
            return

        file_type = None
        if message.document:
            file_type = 'document'
        elif message.photo:
            file_type = 'photo'
        elif message.video:
            file_type = 'video'
        elif message.audio:
            file_type = 'audio'

        if not file_type:
            return

        file_meta = FileIndexer.FILE_TYPES.get(file_type, {'emoji': '📁', 'reward': 5})

        file_data = {
            'file_id': None,
            'file_type': file_type,
            'title': "",
            'description': message.caption or "",
            'group_id': message.chat.id,
            'user_id': message.from_user.id,
            'timestamp': message.date
        }

        if file_type == 'document':
            file_data['file_id'] = message.document.file_id
            file_data['title'] = message.document.file_name
        elif file_type == 'photo':
            file_data['file_id'] = message.photo[-1].file_id
        elif file_type == 'video':
            file_data['file_id'] = message.video.file_id
            file_data['title'] = message.video.file_name or "Vidéo sans titre"
        elif file_type == 'audio':
            file_data['file_id'] = message.audio.file_id
            file_data['title'] = message.audio.title or "Audio sans titre"

        db.set_temp_file_data(message.message_id, file_data)

        keyboard = [[
            InlineKeyboardButton(
                f"🤝 Accepter {file_meta['reward']} crédits",
                callback_data=f"accept_{message.message_id}"
            ),
            InlineKeyboardButton("🖐🏼 Refuser", callback_data="decline")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message.reply_text(
            f"📥 Fichier détecté! Voulez-vous l'indexer pour {file_meta['reward']} crédits?",
            reply_markup=reply_markup
        )

    def handle_accept(update: Update, context: CallbackContext):
        query = update.callback_query
        try:
            message_id = int(query.data.split('_')[1])
            file_data = db.get_temp_file_data(message_id)
            if not file_data:
                query.answer("❌ Fichier introuvable", show_alert=True)
                return

            if not db.is_search_group(file_data['group_id']):
                query.answer("🚫 Groupe non autorisé.", show_alert=True)
                return

            db.index_file(file_data)
            file_type = file_data['file_type']
            reward = FileIndexer.FILE_TYPES[file_type]['reward']
            db.add_credits(file_data['user_id'], reward)

            query.answer(f"✅ Fichier indexé! +{reward} crédits ajoutés.", show_alert=True)
        except Exception as e:
            logger.error(f"Error accepting file: {e}")
            query.answer("❌ Erreur lors de l'indexation", show_alert=True)
        try:
            query.delete_message()
        except Exception:
            pass

    application.add_handler(MessageHandler(
        Filters.document | Filters.photo | Filters.video | Filters.audio,
        handle_file
    ))
    application.add_handler(CallbackQueryHandler(handle_accept, pattern='^accept_'))
