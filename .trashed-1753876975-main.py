from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from utils.memory_full import db
from utils.user_administrator import init_and_start_all_admin_bots_polling
from handlers import bot_linking, commands, language, terms_accept, monetization, pdg_dashboard
from handlers.pdg_alerts import schedule_pdg_alerts
from extensions.handlers import file_indexer, search_engine
from extensions.handlers import config, hooks, scheduler
import logging

BOT_TOKEN = "7794487631:AAG3F3i7IIuYMT_tR18Ma5P-bdBV_VKa5-A"
logging.basicConfig(level=logging.INFO)

async def setup_bot_commands(application):
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
    application = Application.builder().token(BOT_TOKEN).post_init(setup_bot_commands).build()

    # Standard modules
    bot_linking.setup(application)
    commands.setup(application)
    language.setup(application)
    terms_accept.setup(application)
    
    # AI/file/search extensions
    file_indexer.setup(application)
    search_engine.setup(application)
    
    # Custom modules
    config.setup(application)     # 📦 /config + private management
    hooks.setup(application)      # 👥 user hooks (stats + bans + welcome)
    scheduler.setup(application)  # ⏰ recurring auto-send
    
    # New monetization modules
    monetization.setup(application)
    pdg_dashboard.setup(application)
    schedule_pdg_alerts(application)

    # Admin bots (threads)
    init_and_start_all_admin_bots_polling()  # ⚙️ each bot uses same modules

    logging.info("✅ Bot principal lancé avec modules avancés.")
    application.run_polling()

if __name__ == "__main__":
    main()