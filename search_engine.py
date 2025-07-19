import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext
from utils.memory_full import db
from utils.search_ui import format_search_results, create_results_markup

logger = logging.getLogger(__name__)

class SearchEngine:
    @staticmethod
    def register(application):
        async def handle_search(update: Update, context: CallbackContext):
            message = update.message
            user_id = message.from_user.id

            owner_id = db.get_group_owner(message.chat.id)
            if not owner_id:
                await message.reply_text("❌ Aucun administrateur trouvé pour ce groupe.")
                return

            if not db.has_admin_credits(owner_id):
                await message.reply_text("❌ Crédits épuisés pour ce groupe. Veuillez contacter l'administrateur.")
                return

            await message.reply_text("🔍 Entrez votre recherche:")
            db.set_state(user_id, "awaiting_search")

        async def process_search(update: Update, context: CallbackContext):
            try:
                message = update.message
                user_id = message.from_user.id
                query = message.text.strip()
                db.set_state(user_id, None)

                if message.chat.type == "group" and not db.is_search_group(message.chat.id):
                    return

                group_id = message.chat.id if message.chat.type == "group" else db.get_user_search_group(user_id)
                if not group_id:
                    await message.reply_text("❌ Aucun groupe de recherche défini.")
                    return

                # Récupérer le propriétaire pour débiter le crédit
                owner_id = db.get_group_owner(group_id)
                if not owner_id or not db.has_admin_credits(owner_id):
                    await message.reply_text("❌ Crédits de recherche insuffisants. Contactez l'admin.")
                    return

                results = db.search_files(query, group_id=group_id)
                if not results:
                    await message.reply_text("🔍 Aucun résultat trouvé pour votre recherche")
                    return

                response = format_search_results(query, results)
                markup = create_results_markup(results)

                await message.reply_text(
                    response,
                    reply_markup=markup,
                    parse_mode="HTML"
                )

                # Débit du crédit de l'admin
                db.deduct_admin_credit(owner_id)
                db.save_search_history(user_id, message.chat.id, query, "search")

            except Exception as e:
                logger.error(f"Search error: {e}")
                await message.reply_text("❌ Erreur lors de la recherche. Veuillez réessayer.")

        application.add_handler(CommandHandler('search', handle_search))
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.PRIVATE | filters.ChatType.GROUPS),
            process_search
        ))