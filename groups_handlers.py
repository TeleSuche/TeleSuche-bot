from telegram.ext import Application
import logging

logger = logging.getLogger(__name__)

def setup_groups_handlers(application: Application):
    """Centralise tous les handlers liés aux fonctionnalités de groupe"""
    
    # 1. Statistiques utilisateur
    from . import me
    me.setup(application)  # Commande /me
    
    # 2. Gestion des messages épinglés
    from . import pin
    pin.setup(application)  # Commandes /pin, /editpin, etc.
    
    # 3. Modération instantanée - COMMENTÉ CAR MANQUANT
    # from . import action_auto
    # action_auto.setup(application)      # Commandes /delwarn, /delban, etc.
    
    # 4. Commandes de modération
    from . import moderation_commands
    moderation_commands.setup(application)  # Dépend de only_admin()
    
    # 5. Sécurité anti-bot
    from . import antibot_captcha
    antibot_captcha.setup(application)  # Vérification des nouveaux membres
    
    # 6. Tracking et filtrage
    from . import hooks
    hooks.setup(application)            # Tracking messages + mots interdits
    
    # 7. Journalisation des suppressions
    from . import logdel
    logdel.setup(application)           # Commandes /setlog, /logdel
    
    # 8. Configuration du groupe
    from . import setup_config
    setup_config.setup(application)     # Correction : appel standard de setup
    
    # 9. Messages automatisés
    from . import scheduler
    scheduler.setup(application)        # Messages récurrents
    
    # 10. Gestion du statut du bot - IMPORT CORRECT
    from .group_status_handler import register_group_status_handler
    register_group_status_handler(application)