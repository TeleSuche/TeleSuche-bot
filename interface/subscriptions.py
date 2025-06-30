from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from typing import Dict

class SubscriptionManager:
    """Gestion des abonnements avec internationalisation et état"""
    
    PLANS = {
        'essentiel': {
            'title': "🌸 Pack Essentiel",
            'details': "⏳ Durée : 1 mois (renouvelable)\n📦 Groupes : 5\n🎯 Crédits : 50\n🤖 Support IA : Non",
            'price': "0$/mois"
        },
        'avance': {
            'title': "🔅 Pack Avancé",
            'details': "⏳ Durée : 1 mois\n📦 Groupes : 10\n🎯 Crédits : 1000\n🤖 Support IA : Oui",
            'price': "5.99$/mois"
        },
        'premium': {
            'title': "✴️ Pack Premium",
            'details': "⏳ Durée : 1 mois\n📦 Groupes : Illimités\n🎯 Crédits : 5000\n🤖 Support IA + ChatBot",
            'price': "15.99$/mois"
        },
        'pro': {
            'title': "💼 Pack Pro",
            'details': "⏳ Durée : 1 mois\n📦 Groupes illimités\n🎯 Accès API externe\n🔧 Mode expert",
            'price': "25.99$/mois"
        },
        'ultime': {
            'title': "🚀 Pack Ultime",
            'details': "⏳ Durée : 1 mois\n📦 Tout illimité\n📊 Statistiques premium\n🧠 IA complète, multi-requêtes",
            'price': "59.99$/mois"
        }
    }

    @classmethod
    async def show_plans_menu(cls, update: Update, context: CallbackContext):
        """Affiche le menu des abonnements"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception:
            pass

        text = "💎 <b>Choisissez un bouton de plan pour en savoir plus</b>\n----------------------"
        keyboard = [
            [
                InlineKeyboardButton("🌸 Essentiel - 0$", callback_data="plan_essentiel"),
                InlineKeyboardButton("🔅 Avancé - 5.99$", callback_data="plan_avance")
            ],
            [
                InlineKeyboardButton("✴️ Premium - 15.99$", callback_data="plan_premium"),
                InlineKeyboardButton("💼 Pro - 25.99$", callback_data="plan_pro")
            ],
            [InlineKeyboardButton("🚀 Ultime - 59.99$", callback_data="plan_ultime")],
            [InlineKeyboardButton("🔙 Retour", callback_data="go_back")]
        ]

        await query.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    @classmethod
    async def show_plan_detail(cls, update: Update, context: CallbackContext, plan_key: str):
        """Affiche les détails d'un plan spécifique"""
        query = update.callback_query
        await query.answer()
        
        try:
            await query.delete_message()
        except Exception:
            pass

        plan = cls.PLANS[plan_key]
        message = f"<b>{plan['title']}</b>\n\n{plan['details']}\n💰 <b>Prix :</b> {plan['price']}"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💎 S'abonner", callback_data=f"subscribe_{plan_key}"),
                InlineKeyboardButton("🔙 Retour", callback_data="manage_subscriptions")
            ]
        ])

        await query.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

def setup_subscription_handlers(application):
    """Configure les handlers pour les abonnements"""
    # Menu principal
    application.add_handler(
        CallbackQueryHandler(
            SubscriptionManager.show_plans_menu,
            pattern="^manage_subscriptions$"
        )
    )

    # Handlers pour chaque plan
    for plan_key in SubscriptionManager.PLANS.keys():
        application.add_handler(
            CallbackQueryHandler(
                lambda update, context, pk=plan_key: SubscriptionManager.show_plan_detail(update, context, pk),
                pattern=f"^plan_{plan_key}$"
            )
        )