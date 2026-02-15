"""Telegram message/command handlers → calls orchestrator."""
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters


def create_bot(token: str, orchestrator: Any) -> Application:
    """Create and return the Telegram bot application."""
    app = Application.builder().token(token).build()

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user_id = str(update.effective_user.id)
        text = update.message.text or ""
        response = await orchestrator.handle_message(user_id, text)
        await update.message.reply_text(response)

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user_id = str(update.effective_user.id)
        response = await orchestrator.handle_message(user_id, "/start")
        await update.message.reply_text(response)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
