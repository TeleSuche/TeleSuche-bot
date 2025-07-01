import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler
from typing import Optional, Dict
import asyncio

logger = logging.getLogger(__name__)

# Dictionnaire pour stocker les menus actifs {message_id: user_id}
active_menus: Dict[int, int] = {}
# Dictionnaire pour stocker les tâches de suppression {message_id: task}
menu_tasks: Dict[int, asyncio.Task] = {}

def create_group_menu(username: Optional[str] = None) -> tuple[str, InlineKeyboardMarkup]:
    """
    Crée le menu inline pour les groupes avec restriction d'utilisation
    :param username: Nom d'utilisateur à personnaliser
    :return: (texte_du_menu, markup)
    """
    username_display = f"@{username}" if username else "@utilisateur"
    
    menu_text = (
        f"Cher.e {username_display}, voici votre menu d'utilisateur - trice, "
        "vous pouvez l'utiliser pour votre travail ici\n\n"
        "⏳ <b>Disparition après 2 minutes sans toucher</b>"
    )

    # Boutons organisés en 2 lignes de 2
    keyboard = [
        [
            InlineKeyboardButton("🔍 Search", callback_data="group_search"),
            InlineKeyboardButton("⭐ Crédits", callback_data="group_credits")
        ],
        [
            InlineKeyboardButton("⚡ Speed", callback_data="group_speed"),
            InlineKeyboardButton("👥 Amis", callback_data="group_friends")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)

    return menu_text, markup

async def delete_menu(context: CallbackContext, chat_id: int, message_id: int):
    """Supprime le menu et nettoie les données"""
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.warning(f"Erreur suppression menu: {e}")
    finally:
        active_menus.pop(message_id, None)
        menu_tasks.pop(message_id, None)

def schedule_menu_deletion(context: CallbackContext, chat_id: int, message_id: int, delay=120):
    """Planifie la suppression du menu après délai"""
    task = context.application.create_task(
        _delete_menu_after_delay(context, chat_id, message_id, delay)
        )
    menu_tasks[message_id] = task

async def _delete_menu_after_delay(context: CallbackContext, chat_id: int, message_id: int, delay: int):
    """Coroutine pour suppression différée"""
    await asyncio.sleep(delay)
    await delete_menu(context, chat_id, message_id)

def cancel_menu_deletion(message_id: int):
    """Annule la suppression programmée du menu"""
    if message_id in menu_tasks:
        menu_tasks[message_id].cancel()
        del menu_tasks[message_id]

async def show_group_menu(update: Update, context: CallbackContext):
    """Handler pour afficher le menu de groupe"""
    try:
        user = update.effective_user
        username = user.username or user.first_name
        menu_text, markup = create_group_menu(username)
        
        sent_msg = await update.message.reply_text(
            menu_text,
            parse_mode="HTML",
            reply_markup=markup
        )
        
        # Stocke l'association message_id -> user_id
        active_menus[sent_msg.message_id] = user.id
        await cleanup_expired_menus()  # Nettoie les anciens menus
        
        # Planifie la suppression après 2 minutes
        schedule_menu_deletion(context, sent_msg.chat_id, sent_msg.message_id)
        
    except Exception as e:
        logger.error(f"Erreur affichage menu groupe: {e}")
        await update.message.reply_text("❌ Impossible d'afficher le menu. Veuillez réessayer.")

async def handle_group_actions(update: Update, context: CallbackContext):
    """Handler pour les actions du menu groupe"""
    query = update.callback_query
    await query.answer()
    
    try:
        # Annule la suppression programmée
        cancel_menu_deletion(query.message.message_id)
        
        # Vérification de l'utilisateur autorisé
        owner_id = active_menus.get(query.message.message_id)
        
        # Si l'utilisateur n'est pas le propriétaire du menu
        if owner_id != query.from_user.id:
            await query.answer(
                "⛔ Désolé, ce menu est réservé à l'utilisateur qui l'a demandé.",
                show_alert=True
            )
            # Replanifie la suppression après 2 minutes
            schedule_menu_deletion(context, query.message.chat_id, query.message.message_id)
            return

        # Si c'est le propriétaire
        await query.answer(
            "⏳ Cette fonctionnalité est en cours de maintenance.",
            show_alert=True
        )
        
        # Replanifie la suppression après 2 minutes
        schedule_menu_deletion(context, query.message.chat_id, query.message.message_id)
            
    except Exception as e:
        logger.error(f"Erreur action groupe: {e}")
        await query.answer("❌ Erreur lors du traitement")

async def cleanup_expired_menus(max_age_minutes=5):
    """Nettoie les menus actifs expirés (5 minutes par défaut)"""
    now = datetime.now()
    expired = [msg_id for msg_id, user_id in active_menus.items() 
               if (now - datetime.fromtimestamp(msg_id >> 32)).total_seconds() > max_age_minutes * 60]
    for msg_id in expired:
        active_menus.pop(msg_id, None)
        if msg_id in menu_tasks:
            menu_tasks[msg_id].cancel()
            menu_tasks.pop(msg_id, None)

def setup_group_handlers(application):
    """Enregistre les handlers pour les groupes"""
    application.add_handler(
        CommandHandler("groupmenu", show_group_menu, chat_types=['group', 'supergroup'])
    )
    application.add_handler(
        CallbackQueryHandler(handle_group_actions, pattern="^group_")
    )
