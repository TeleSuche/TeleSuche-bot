from telegram import Update, ChatMember
from telegram.ext import ContextTypes, CommandHandler, ChatMemberHandler
from telegram.constants import ChatMemberStatus, ChatType

def register_group_status_handler(application):
    # Handler pour les changements de statut du bot
    async def handle_group_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        bot = context.bot
        bot_id = bot.id
        event = update.my_chat_member
        chat = event.chat
        actor = event.from_user

        try:
            member = await bot.get_chat_member(chat.id, bot_id)
        except Exception as e:
            print(f"[Erreur permissions] : {e}")
            return

        # Bot ajouté comme simple membre
        if event.new_chat_member.status == ChatMemberStatus.MEMBER:
            try:
                await bot.send_message(
                    chat.id,
                    "🤖 Je viens d'être ajouté dans ce groupe.\n\n"
                    "⚙️ Veuillez m'ajouter comme administrateur pour activer toutes les fonctionnalités (facultatif)."
                )
            except Exception as e:
                print(f"[Erreur message groupe] : {e}")

            try:
                await bot.send_message(
                    actor.id,
                    f"✅ Je suis ajouté comme <b>membre</b> dans le groupe :\n"
                    f"📌 <b>{chat.title}</b>\n🆔 ID : <code>{chat.id}</code>\n\n"
                    "🔧 Commandes disponibles :\n"
                    "/voir_mes_permissions\n"
                    "/retirer_moi_du_groupe",
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"[Erreur message privé] : {e} - L'utilisateur n'a peut-être pas démarré le bot")
            return

        # Bot promu administrateur
        if event.new_chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            try:
                # Accès correct aux permissions
                perms = event.new_chat_member
                checks = {
                    "🖼️ Photos": perms.can_send_media_messages,
                    "📹 Vidéos": perms.can_send_media_messages,
                    "🎧 Audios": perms.can_send_audios,
                    "📚 Documents": perms.can_send_documents
                }

                access_status = ""
                for label, ok in checks.items():
                    access_status += f"{label} {'✅' if ok else '❌'}\n"

                # Message dans le groupe
                text_group = (
                    f"👏🏼 J'ai été ajouté dans le groupe <b>{chat.title}</b> comme administrateur.\n\n"
                    f"👤 Action effectuée par : <b>{actor.first_name}</b>\n\n"
                    f"📥 J'ai maintenant accès aux fichiers :\n{access_status}\n"
                    f"🤖 Bot hébergé par : @TeleSucheBot"
                )

                await bot.send_message(chat.id, text_group, parse_mode="HTML")
            except Exception as e:
                print(f"[Erreur message groupe admin] : {e}")

            try:
                # Message privé
                text_private = (
                    f"✅ Je suis promu administrateur dans le groupe :\n"
                    f"📌 <b>{chat.title}</b>\n🆔 ID : <code>{chat.id}</code>\n\n"
                    "🔧 Commandes disponibles :\n"
                    "/voir_mes_permissions\n"
                    "/retirer_moi_admin"
                )

                await bot.send_message(actor.id, text_private, parse_mode="HTML")
            except Exception as e:
                print(f"[Erreur message privé admin] : {e} - L'utilisateur n'a peut-être pas démarré le bot")

    # Commandes
    async def voir_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await message.reply_text("❌ Cette commande fonctionne uniquement dans un groupe.")
            return

        try:
            perms = (await context.bot.get_chat_member(message.chat.id, context.bot.id)).privileges
            text = (
                "🔎 <b>Mes permissions dans ce groupe</b> :\n\n"
                f"🖼️ Envoyer médias : {'✅' if perms.can_send_media_messages else '❌'}\n"
                f"📚 Envoyer documents : {'✅' if perms.can_send_documents else '❌'}\n"
                f"🗑️ Supprimer messages : {'✅' if perms.can_delete_messages else '❌'}"
            )
            await message.reply_text(text, parse_mode="HTML")
        except Exception as e:
            print(f"[Erreur permissions] : {e}")
            await message.reply_text("⚠️ Impossible de lire les permissions actuelles.")

    async def retirer_du_groupe(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            try:
                await message.reply_text("👋 Je quitte ce groupe.")
                await context.bot.leave_chat(message.chat.id)
            except Exception as e:
                print(f"[Erreur leave] : {e}")
                await message.reply_text("❌ Je n'ai pas pu quitter ce groupe.")

    async def retirer_admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🔐 Je ne peux pas me retirer des administrateurs moi-même.\n"
            "Veuillez le faire manuellement dans les paramètres du groupe."
        )

    # Enregistrement des handlers
    application.add_handler(ChatMemberHandler(handle_group_status, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("voir_mes_permissions", voir_permissions))
    application.add_handler(CommandHandler("retirer_moi_du_groupe", retirer_du_groupe))
    application.add_handler(CommandHandler("retirer_moi_admin", retirer_admin_info))