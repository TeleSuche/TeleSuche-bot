#!/usr/bin/env python3
"""Point d'entrée principal de l'application"""
import sys
import os
import logging
import pkgutil
import asyncio
import warnings
import json
import signal
import socket
import time

from pathlib import Path

# Configuration du chemin avant tous les autres imports
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'utils'))

# Ignorer les warnings spécifiques
warnings.filterwarnings("ignore", category=UserWarning, message="pkg_resources is deprecated")

# Patch de compatibilité Python 3.12
if sys.version_info >= (3, 12):
    try:
        pkgutil.ImpImporter
    except AttributeError:
        class ImpImporter:
            """Patch pour la compatibilité Python 3.12"""
            def find_module(self, fullname, path=None):
                return None
        pkgutil.ImpImporter = ImpImporter

from telegram import BotCommand, Update
from telegram.ext import Application, CallbackContext
from telegram.request import HTTPXRequest
from telegram.error import TimedOut

# Import des modules personnalisés
from utils.user_administrator import (
    init_and_start_all_admin_bots_polling,
    error_handler as admin_error_handler
)
from handlers import bot_linking, commands, language, terms_accept, pdg_dashboard
from handlers.pdg_alerts import schedule_pdg_alerts
from handlers.log_summary import setup as setup_log_summary
from handlers.bot_deletion_pin import setup_deletion_pin_handler

from schedulers.daily_log_report import setup_daily_report
from config import config as app_config
from utils.memory_full import db

# Configuration du logger
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Chargement du token principal depuis tokens.json
def load_bot_token():
    try:
        tokens_path = PROJECT_ROOT / 'tokens.json'
        if not tokens_path.exists():
            logger.error("Fichier tokens.json introuvable.")
            return None
        with open(tokens_path, 'r') as f:
            tokens = json.load(f)
            return tokens.get('main_bot')
    except Exception as e:
        logger.error(f"Erreur chargement token: {e}")
        return None

BOT_TOKEN = load_bot_token()
if not BOT_TOKEN:
    logger.critical("Token principal manquant!")
    sys.exit(1)

async def setup_bot_commands(application):
    """Configure les commandes du bot"""
    commands_list = [
        BotCommand("start", "démarrage du menu principal"),
        BotCommand("ensavoirplus", "Connaître TeleSucheBot"),
        BotCommand("creeunbot", "Connecter votre nouveau bot"),
        BotCommand("mybots", "Voir vos bots connectés"),
        BotCommand("support", "Contacter le support"),
        BotCommand("planinfo", "Voir votre plan actuel"),
        BotCommand("statistiques", "Voir vos statistiques bot"),
        BotCommand("aide", "Consulter le menu d'aide"),
        BotCommand("services", "Consulter le menu de services"),
        BotCommand("lang", "Changer la langue du bot"),
        BotCommand("starter", "réinitialiser le bot"),
        BotCommand("config", "Configurer votre bot (privé)")
    ]
    await application.bot.set_my_commands(commands_list)

async def global_error_handler(update: Update, context: CallbackContext):
    """Gestionnaire global d'erreurs"""
    try:
        raise context.error
    except TimedOut:
        logger.warning("Timeout détecté, réessai automatique...")
        if update and update.effective_message:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⌛ Délai d'attente dépassé, réessai...",
                reply_to_message_id=update.effective_message.message_id
            )
    except Exception as e:
        logger.error(f"Erreur non gérée: {e}")
        if update and update.effective_message:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Une erreur inattendue s'est produite. ERR_BLM_013. Veillez notifié le support @TeleSucheSupport.",
                reply_to_message_id=update.effective_message.message_id
            )

def check_network_connection():
    """Vérifie la connectivité réseau avant de démarrer les bots"""
    max_retries = 5
    retry_delay = 10  # secondes
    
    for attempt in range(1, max_retries + 1):
        try:
            # Vérification de la résolution DNS
            socket.getaddrinfo("api.telegram.org", 443)
            logger.info("Connectivité réseau vérifiée")
            return True
        except socket.gaierror as e:
            logger.warning("Échec résolution DNS (tentative %d/%d): %s", attempt, max_retries, e)
            time.sleep(retry_delay)
    
    logger.error("Échec de la vérification réseau après %d tentatives", max_retries)
    return False

async def start_bot_polling(application):
    """Démarre le polling d'un bot de manière asynchrone"""
    try:
        logger.info("Initialisation du bot...")
        await application.initialize()
        await application.start()
        logger.info("Démarrage du polling...")
        await application.updater.start_polling()
        logger.info("Polling démarré avec succès")
    except Exception as e:
        logger.error(f"Erreur démarrage polling: {e}")
        raise

async def stop_bot_polling(application):
    """Arrête le polling d'un bot proprement"""
    try:
        if application.updater.running:
            logger.info("Arrêt du polling...")
            await application.updater.stop()
        if application.running:
            logger.info("Arrêt du bot...")
            await application.stop()
        logger.info("Nettoyage du bot...")
        await application.shutdown()
        logger.info("Bot arrêté proprement")
    except Exception as e:
        logger.error(f"Erreur arrêt bot: {e}")

async def main_async():
    """Fonction principale asynchrone"""
    # Vérification de la connectivité réseau
    if not check_network_connection():
        logger.critical("Impossible d'établir une connexion réseau. Arrêt.")
        sys.exit(1)

    # Vérification des imports critiques
    try:
        from utils import memory_full
        logger.info("Import utils réussi")
    except ImportError as e:
        logger.critical("Échec import utils: %s", e)
        logger.critical("Chemin Python: %s", sys.path)
        raise

    # Initialisation de la configuration PDG
    if not hasattr(db, 'pdg_config'):
        db.pdg_config = {}

    # Mettre à jour la configuration PDG
    if app_config.PDG_BOT_TOKEN:
        db.pdg_config.update({
            "token": app_config.PDG_BOT_TOKEN,
            "bot_id": app_config.PDG_BOT_ID,
            "owner": app_config.PDG_USER_ID[0],
            "is_active": True
        })
        logger.info("Configuration PDG initialisée")

    # Configuration des timeouts HTTP
    request = HTTPXRequest(
        connect_timeout=20.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )

    # Création de l'application principale
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(request)
        .concurrent_updates(True)  # Active la JobQueue
        .post_init(setup_bot_commands)
        .build()
    )

    # Ajout des gestionnaires d'erreurs
    application.add_error_handler(global_error_handler)
    application.add_error_handler(admin_error_handler)

    # Enregistrement des handlers principaux
    logger.info("Enregistrement des handlers du bot principal")
    bot_linking.setup(application)
    commands.setup(application)
    language.setup(application)
    terms_accept.setup(application)
    pdg_dashboard.setup(application)
    setup_log_summary(application)
    schedule_pdg_alerts(application)
    setup_deletion_pin_handler(application)
    
    # Configurer le rapport journalier
    setup_daily_report(application)

    # Lancement des bots administrateurs
    await init_and_start_all_admin_bots_polling()

    # Démarrer le bot principal
    logger.info("Démarrage du bot principal...")
    main_bot_task = asyncio.create_task(start_bot_polling(application))

    # Démarrer le bot PDG si configuré
    pdg_task = None
    if db.pdg_config.get("token"):
        from pdg_bot import start_pdg_bot
        pdg_task = asyncio.create_task(start_pdg_bot())
        logger.info("Bot PDG démarré")

    # Gestion des signaux d'arrêt
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Signal d'arrêt reçu")
        stop_event.set()
    
    loop = asyncio.get_running_loop()
    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(
            getattr(signal, signame),
            signal_handler
        )

    # Attendre l'événement d'arrêt
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("Tâche principale annulée")

    logger.info("Arrêt en cours...")

    # Arrêt du bot principal
    logger.info("Arrêt du bot principal...")
    main_bot_task.cancel()
    try:
        await main_bot_task
    except asyncio.CancelledError:
        pass
    await stop_bot_polling(application)

    # Arrêt du bot PDG
    if pdg_task:
        logger.info("Arrêt du bot PDG...")
        from pdg_bot import stop_pdg_bot
        await stop_pdg_bot()
        pdg_task.cancel()
        try:
            await pdg_task
        except asyncio.CancelledError:
            pass

    logger.info("Arrêt complet réussi")

def main():
    """Fonction principale d'exécution"""
    try:
        # Création de la boucle d'événements
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_async())
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur (Ctrl+C)")
    except Exception as e:
        logger.critical("Échec du démarrage du bot: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        # Nettoyage final
        tasks = asyncio.all_tasks(loop=asyncio.get_event_loop())
        for task in tasks:
            task.cancel()
        loop.close()
        logger.info("Application complètement arrêtée")

if __name__ == "__main__":
    required_dirs = ["utils", "handlers", "extensions", "schedulers"]
    missing = [d for d in required_dirs if not (PROJECT_ROOT / d).exists()]

    if missing:
        print(f"ERREUR: Dossiers manquants: {', '.join(missing)}")
        sys.exit(1)

    main()
