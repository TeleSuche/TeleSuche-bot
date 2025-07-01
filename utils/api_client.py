import logging
logger = logging.getLogger(__name__)
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

async def send_to_user_bot(bot_token: str, chat_id: int, message: str) -> bool:
    """
    Envoie un message à un utilisateur via un bot Telegram (version asynchrone)
    
    Args:
        bot_token: Le token du bot Telegram
        chat_id: L'ID du chat destinataire
        message: Le message à envoyer
        
    Returns:
        bool: True si l'envoi a réussi, False sinon
    """
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        return True
    except TelegramError as e:
        logger.error(f"Erreur d'envoi au bot utilisateur: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}", exc_info=True)
        return False

async def validate_bot_token(token: str) -> bool:
    """
    Valide un token de bot Telegram (version asynchrone)
    
    Args:
        token: Le token du bot à valider
        
    Returns:
        bool: True si le token est valide, False sinon
    """
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        return me is not None
    except TelegramError as e:
        logger.error(f"[validate_bot_token] Token invalide: {e}")
        return False
    except Exception as e:
        logger.error(f"[validate_bot_token] Erreur inattendue: {e}")
        return False