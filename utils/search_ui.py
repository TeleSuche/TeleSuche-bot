from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from extensions.handlers import referral_ui  # ✅ Correction ici

def format_search_results(query: str, results: list) -> str:
    """Formate les résultats de recherche pour l'affichage"""
    msg = f"🔍 <b>Résultats pour '{query}'</b>\n\n"
    
    for i, result in enumerate(results[:5]):  # Limiter à 5 résultats
        emoji = "📄"
        if result['file_type'] == 'video': emoji = "🎬"
        elif result['file_type'] == 'photo': emoji = "🖼️"
        elif result['file_type'] == 'audio': emoji = "🎧"
        
        title = result['title'] or f"Fichier {result['file_type']}"
        msg += f"{i+1}. {emoji} <b>{title}</b>\n"
        
        if result.get('description'):
            msg += f"   📝 {result['description'][:50]}{'...' if len(result['description']) > 50 else ''}\n"
            
        msg += "\n"
    
    if len(results) > 5:
        msg += f"\n🔎 <i>{len(results)-5} résultats supplémentaires non affichés</i>"
    
    return msg

def create_results_markup(results: list) -> InlineKeyboardMarkup:
    """Crée un clavier pour les résultats de recherche"""
    buttons = []
    
    for i, result in enumerate(results[:3]):
        buttons.append(
            InlineKeyboardButton(
                text=f"📥 Télécharger #{i+1}",
                callback_data=f"download_{result['file_id']}"
            )
        )
    
    if len(results) > 3:
        buttons.append(
            InlineKeyboardButton(
                text="🔍 Plus de résultats",
                callback_data="more_results"
            )
        )
    
    return InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])

async def handle_invite_button(update: Update, context: CallbackContext):
    """Gère le bouton d'invitation"""
    query = update.callback_query
    user_id = query.from_user.id
    markup = referral_ui.get_referral_markup(user_id)
    
    await query.answer()
    await query.edit_message_text(
        text="🎉 <b>Gagnez des crédits en invitant des amis!</b>\n\n"
             "Partagez votre lien personnel et recevez:\n"
             "• 0.5$ en crédits par ami invité\n"
             "• Commission sur leurs abonnements\n\n"
             "Votre administrateur reçoit aussi des récompenses!",
        parse_mode="HTML",
        reply_markup=markup
    )

def setup_search_handlers(application):
    """Enregistre les handlers de recherche"""
    application.add_handler(
        CallbackQueryHandler(
            handle_invite_button,
            pattern="^invite_and_earn$"
        )
    )