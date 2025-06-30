from telegram.ext import Application
from . import (
    me,
    pin,
    action_auto,
    antibot_captcha,
    group_status_handler,
    hooks,
    logdel,
    moderation_commands,
    scheduler,
    setup_config
)

def setup_groups_handlers(application: Application):
    """Centralise tous les handlers liés aux fonctionnalités de groupe"""
    
    # 1. Statistiques utilisateur
    me.setup(application)  # Commande /me
    
    # 2. Gestion des messages épinglés
    pin.setup(application)  # Commandes /pin, /editpin, etc.
    
    # 3. Modération instantanée
    action_auto.setup(application)      # Commandes /delwarn, /delban, etc.
    
    # 4. Commandes de modération
    moderation_commands.setup(application)  # Dépend de only_admin()
    
    # 5. Sécurité anti-bot
    antibot_captcha.setup(application)  # Vérification des nouveaux membres
    
    # 6. Tracking et filtrage
    hooks.setup(application)            # Tracking messages + mots interdits
    
    # 7. Journalisation des suppressions
    logdel.setup(application)           # Commandes /setlog, /logdel
    
    # 8. Configuration du groupe
    setup_config.setup(application)     # Menu de config (dépend de only_admin)
    
    # 9. Messages automatisés
    scheduler.setup(application)        # Messages récurrents
    
    # 10. Gestion du statut du bot
    group_status_handler.register_group_status_handler(application)