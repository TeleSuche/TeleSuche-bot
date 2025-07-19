from telegram.ext import Application

def main():
    """Point d'entrée principal pour l'exécution du bot"""
    application = Application.builder().token("7794487631:AAG8Du5ajsGf0FTcJUUrkYEr86pwMO1f9eg").build()
    application.run_polling()

if __name__ == "__main__":
    main()
