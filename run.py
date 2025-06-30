from telegram.ext import Application
from main import setup_bot_commands

def main():
    application = Application.builder().token("7794487631:AAG3F3i7IIuYMT_tR18Ma5P-bdBV_VKa5-A").build()
    application.run_polling()

if __name__ == "__main__":
    main()
