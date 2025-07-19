# menu_utils.py
from telegram import Update
from telegram.ext import CallbackContext
from utils.memory_full import db
from utils.keyboards import main_menu_keyboard

async def show_main_menu(update: Update, context: CallbackContext) -> None:
    """Affiche le menu principal avec la nouvelle disposition"""
    user_id = update.effective_user.id
    lang = db.get_user_language(user_id) or 'fr'

    # Nouveau texte d'accueil selon votre style exact
    menu_texts = {
        'fr': """
🔥 TeleSucheBot 🚀

Créez des bots : 
🔍 Pour des recherches 
💎 Gérer vos abonnements. 
⚙️ Automatiser la modération 
de vos groupes. 
🤖 Développer des assistants 
IA puissants.
🛍️ Créer des boutiques digitales
et tant d'autres services....

✅ Compte est actif
""",
        'en': """
🔥 TeleSucheBot 🚀

Create bots for: 
🔍 Smart searches 
💎 Manage your subscriptions. 
⚙️ Automate moderation of 
your groups. 
🤖 Develop powerful 
AI assistants.
🛍️ Create digital stores
and many other services....

✅ Account is active
""",
        'es': """
🔥 TeleSucheBot 🚀

Crea bots para: 
🔍 Búsquedas inteligentes 
💎 Gestionar sus suscripciones. 
⚙️ Automatizar moderación de 
tus grupos. 
🤖 Desarrollar asistentes 
IA potentes.
🛍️ Crear tiendas digitales
y muchos otros servicios....

✅ Cuenta está activa
""",
        'de': """
🔥 TeleSucheBot 🚀

Erstellen Sie Bots für: 
🔍 Intelligente Suche 
💎 Verwalten Sie Abonnements. 
⚙️ Automatisieren Sie die 
Gruppenmoderation. 
🤖 Entwickeln Sie leistungsstarke
KI-Assistenten.
🛍️ Digitale Shops erstellen
und viele weitere Dienste....

✅ Konto ist aktiv
""",
        'ru': """
🔥 TeleSucheBot 🚀

Создавайте ботов для: 
🔍 Умного поиска 
💎 Управления подписками. 
⚙️ Автоматизации модерации 
ваших групп. 
🤖 Разработки мощных 
AI-ассистентов.
🛍️ Создания цифровых магазинов
и многих других сервисов....

✅ Аккаунт активен
"""
    }

    text = menu_texts.get(lang, menu_texts['fr'])

    # Ajout des informations personnalisées (inchangé)
    user_bots = db.get_user_bots(user_id)
    if user_bots:
        bot_count = len(user_bots)
        plan = db.get_user_plan(user_id) or "sub_basic"
        
        plan_names = {
            "sub_basic": "🌸 Essentiel",
            "sub_avance": "☀️ Avancé",
            "sub_premium": "🏵️Premium",
            "sub_pro": "🌼 Pro",
            "sub_ultime": "💎 Ultime"
        }
        
        plan_text = plan_names.get(plan, plan)
        
        user_info = (
            f"\n\n👤 <b>Votre compte</b>\n"
            f"• Bots actifs: {bot_count}\n"
            f"• Plan: {plan_text}"
        ) if lang == 'fr' else (
            f"\n\n👤 <b>Your Account</b>\n"
            f"• Active bots: {bot_count}\n"
            f"• Plan: {plan_text}"
        )
        
        text += user_info

    # Séparateur avant le menu
    text += "\n---------------------"

    # Envoi du message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=main_menu_keyboard(lang),
            parse_mode="HTML",
            disable_web_page_preview=True
        )