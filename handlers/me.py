# handlers/me.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application
from utils.memory_full import db

async def handle_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("❗ Utilisez cette commande en privé avec le bot.")

    user = update.effective_user
    user_id = user.id
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "(pas de username)"

    stats = []

    # Stats
    for chat_id, counts in db.get("message_count", {}).items():
        if user_id in counts:
            stats.append((chat_id, counts[user_id]))

    # Warns
    warn_count = 0
    for chat_id, warns in db.get("warnings_store", {}).items():
        if user_id in warns:
            warn_count += len(warns[user_id])

    # Rôle (à venir)
    role = "Utilisateur"
    # Règlement (1er groupe où trouvé)
    rules_text = None
    for chat_id, rule in db.get("rules_text", {}).items():
        if rule:
            rules_text = rule
            break

    lines = [
        f"👤 <b>{full_name}</b> ({username})",
        f"🆔 <code>{user_id}</code>",
        f"📊 Messages envoyés: <b>{sum(s[1] for s in stats)}</b>",
        f"⚠️ Avertissements: <b>{warn_count}</b>",
        f"🎭 Rôle: <b>{role}</b>"
    ]

    if rules_text:
        lines.append("\n📜 <b>Règlement du groupe :</b>\n" + rules_text)

    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

# --- SETUP ---

def setup(application: Application):
    application.add_handler(CommandHandler("me", handle_me))