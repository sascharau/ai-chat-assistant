import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler as TgHandler, filters, ApplicationBuilder

from core.channels import register_channel
from core.channels.base import Channel, IncomingMessage, MessageHandler
from core.config import Config


logger = logging.getLogger(__name__)


class TelegramChannel(Channel):
    """Telegram-Bot via python-telegram-bot."""

    def __init__(self, token: str, assistant_name: str):
        self._token = token
        self._assistant_name = assistant_name
        self._app = ApplicationBuilder().token(token).build()

    @property
    def name(self) -> str:
        return "telegram"

    async def connect(self, handler: MessageHandler) -> None:

        async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return

            chat = update.message.chat
            user = update.message.from_user
            is_group = chat.type in ("group", "supergroup")

            msg = IncomingMessage(
                chat_id=f"telegram:{chat.id}",
                sender=user.username or str(user.id) if user else "unknown",
                sender_name=user.first_name or "Unknown" if user else "Unknown",
                content=update.message.text,
                timestamp=datetime.now(timezone.utc),
                channel="telegram",
                is_group=is_group,
            )
            await handler(msg)

        self._app.add_handler(TgHandler(filters.TEXT & ~filters.COMMAND, on_message))

        # Start polling in its own task
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        logger.info("Telegram bot started")

    async def send_message(self, chat_id: str, text: str) -> None:
        telegram_id = int(chat_id.removeprefix("telegram:"))
        # Telegram: max 4096 characters per message
        for chunk in _split_text(text, max_len=4096):
            await self._app.bot.send_message(
                chat_id=telegram_id,
                text=chunk,
                parse_mode="Markdown",
            )

    def owns_chat_id(self, chat_id: str) -> bool:
        return chat_id.startswith("telegram:")

    async def shutdown(self) -> None:
        await self._app.updater.stop()
        await self._app.stop()
        await self._app.shutdown()


def _split_text(text: str, max_len: int) -> list[str]:
    """Split text at character limit, preferring line breaks."""
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Split at the last newline before the limit
        split_idx = text.rfind("\n", 0, max_len)
        if split_idx <= 0:
            split_idx = max_len
        chunks.append(text[:split_idx])
        text = text[split_idx:].lstrip()
    return chunks


# --- Self-Registration ---
def _factory(config: Config) -> TelegramChannel | None:
    if not config.telegram_bot_token:
        logger.debug("Telegram: no TELEGRAM_BOT_TOKEN set, skipping")
        return None
    return TelegramChannel(config.telegram_bot_token, config.assistant_name)


register_channel("telegram", _factory)