import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
# main.py - Bot Telegram principal avec compatibilité Python 3.12

import sys
import pkgutil
import logging

# Patch de compatibilité pour Python 3.12
if sys.version_info >= (3, 12):
    try:
        # Vérifier si l'attribut existe déjà
        pkgutil.ImpImporter
    except AttributeError:
        # Créer une implémentation minimaliste
        class ImpImporter:
            def find_module(self, fullname, path=None):
                return None
        pkgutil.ImpImporter = ImpImporter

from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from utils.memory_full import db
from utils.user_administrator import init_and_start_all_admin_bots_polling
from handlers import bot_linking, commands, language, terms_accept, monetization, pdg_dashboard
from handlers.pdg_alerts import schedule_pdg_alerts
from extensions.handlers import file_indexer, search_engine
from extensions.handlers import config, hooks, scheduler

# Configuration du logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token du bot principal
BOT_TOKEN = "7794487631:AAG3F3i7IIuYMT_tR18Ma5P-bdBV_VKa5-A"

async def setup_bot_commands(application):
    """Configure les commandes du bot pour l'interface Telegram"""
    await application.bot.set_my_commands([
        BotCommand("ensavoirplus", "Connaître TeleSucheBot"),
        BotCommand("creeunbot", "Connecter votre nouveau bot"),
        BotCommand("mybots", "Voir vos bots connectés"),
        BotCommand("monwallet", "Consulter votre portefeuille"),
        BotCommand("monabonnement", "S’abonner à une offre"),
        BotCommand("supporttechnique", "Contacter le support"),
        BotCommand("statistiques", "Voir vos statistiques bot"),
        BotCommand("aide", "Consulter le menu d'aide"),
        BotCommand("lang", "Changer la langue du bot"),
        BotCommand("config", "Configurer votre bot (privé)")
    ])

def main():
    """Point d'entrée principal du bot"""
    try:
        # Création de l'application
        application = Application.builder().token(BOT_TOKEN).post_init(setup_bot_commands).build()
        
        # Modules standards
        bot_linking.setup(application)
        commands.setup(application)
        language.setup(application)
        terms_accept.setup(application)
        
        # Extensions IA/fichier/recherche
        file_indexer.setup(application)
        search_engine.setup(application)
        
        # Modules personnalisés
        config.setup(application)     # Configuration
        hooks.setup(application)      # Hooks utilisateurs
        scheduler.setup(application)  # Planification
        
        # Modules de monétisation
        monetization.setup(application)
        pdg_dashboard.setup(application)
        schedule_pdg_alerts(application)

        # Lancement des bots administrateurs
        init_and_start_all_admin_bots_polling()

        logger.info("✅ Bot principal lancé avec succès")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Échec du démarrage du bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()