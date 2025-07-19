# pdg_bot.py
import logging
import asyncio
from telegram.ext import Application
from config import config as app_config
from schedulers.daily_log_report import setup_daily_report
from handlers.pdg_dashboard import setup as setup_pdg_dashboard
from utils.memory_full import db

logger = logging.getLogger(__name__)

pdg_application = None

async def start_pdg_bot():
    """Démarre le bot PDG dans la boucle existante"""
    global pdg_application
    try:
        if not db.pdg_config.get("token"):
            logger.error("Token PDG non configuré!")
            return

        logger.info("Démarrage du bot PDG...")
        
        # Configuration de l'application PDG
        pdg_application = (
            Application.builder()
            .token(db.pdg_config["token"])
            .concurrent_updates(True)
            .build()
        )
        
        # Configuration des handlers
        setup_pdg_dashboard(pdg_application)
        setup_daily_report(pdg_application)
        
        logger.info("Initialisation du bot PDG...")
        await pdg_application.initialize()
        await pdg_application.start()
        logger.info("Démarrage du polling pour le bot PDG...")
        await pdg_application.updater.start_polling()
        logger.info("Bot PDG démarré avec succès")
        
        # Attendre indéfiniment
        await asyncio.Future()
        
    except asyncio.CancelledError:
        logger.info("Arrêt du bot PDG demandé")
    except Exception as e:
        logger.error(f"Erreur démarrage bot PDG: {e}")
        await stop_pdg_bot()

async def stop_pdg_bot():
    """Arrête le bot PDG proprement"""
    global pdg_application
    if pdg_application:
        logger.info("Arrêt du bot PDG...")
        try:
            if pdg_application.updater and pdg_application.updater.running:
                await pdg_application.updater.stop()
            if pdg_application.running:
                await pdg_application.stop()
            await pdg_application.shutdown()
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du bot PDG: {e}")
        pdg_application = None
    logger.info("Bot PDG arrêté proprement")