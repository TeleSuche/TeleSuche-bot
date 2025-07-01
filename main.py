import logging
logger = logging.getLogger(__name__)
#!/usr/bin/env python3
# main.py - Bot Telegram principal avec compatibilité Python 3.12

import sys
import pkgutil
import logging
from pathlib import Path

# CORRECTION CRITIQUE - Ajout du chemin racine en PREMIER
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Patch de compatibilité pour Python 3.12
if sys.version_info >= (3, 12):
    try:
        pkgutil.ImpImporter
    except AttributeError:
        class ImpImporter:
            def find_module(self, fullname, path=None):
                return None
        pkgutil.ImpImporter = ImpImporter

from telegram import BotCommand
from telegram.ext import Application
from utils.user_administrator import init_and_start_all_admin_bots_polling
from handlers import bot_linking, commands, language, terms_accept, monetization, pdg_dashboard
from handlers.pdg_alerts import schedule_pdg_alerts
from extensions.handlers import file_indexer, search_engine
from config import setup_config_handlers, hooks, scheduler
from pdg_bot import init_pdg_bot  # Import du gestionnaire PDG

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
        # Vérification des imports critiques
        try:
            from utils import memory_full
            logger.info("✅ Import utils réussi")
        except ImportError as e:
            logger.critical(f"Échec import utils: {e}")
            logger.critical("Chemin Python: %s", sys.path)
            raise

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
        setup_config_handlers(application)     # Configuration
        hooks.setup(application)      # Hooks utilisateurs
        scheduler.setup(application)  # Planification
        
        # Modules de monétisation
        monetization.setup(application)
        pdg_dashboard.setup(application)
        schedule_pdg_alerts(application)

        # Lancement des bots administrateurs
        init_and_start_all_admin_bots_polling()
        
        # Démarrer le bot PDG si configuré
        init_pdg_bot()

        logger.info("✅ Bot principal lancé avec succès")
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Échec du démarrage du bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Vérification supplémentaire de la structure
    required_dirs = ["utils", "handlers", "extensions"]
    missing = [d for d in required_dirs if not (PROJECT_ROOT / d).exists()]
    
    if missing:
        print(f"ERREUR: Dossiers manquants: {', '.join(missing)}")
        print("Structure requise:")
        print(f"- {PROJECT_ROOT}/utils/ (contient memory_full.py)")
        print(f"- {PROJECT_ROOT}/handlers/")
        print(f"- {PROJECT_ROOT}/extensions/")
        sys.exit(1)
        
    main()