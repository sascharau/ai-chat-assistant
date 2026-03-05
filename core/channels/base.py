import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable


@dataclass
class IncomingMessage:
    chat_id: str
    sender: str
    sender_name: str
    content: str
    timestamp: datetime
    channel: str
    is_group: bool


# Type alias for the message handler callback
MessageHandler = Callable[[IncomingMessage], Awaitable[None]]


class Channel(abc.ABC):
    """Abstract base class for all messaging channels."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Channel name, e.g. 'telegram', 'discord'."""

    @abc.abstractmethod
    async def connect(self, handler: MessageHandler) -> None:
        """Connect and forward incoming messages to the handler."""

    @abc.abstractmethod
    async def send_message(self, chat_id: str, text: str) -> None:
        """Send a message to a chat."""

    @abc.abstractmethod
    def owns_chat_id(self, chat_id: str) -> bool:
        """Check if a chat ID belongs to this channel."""

    async def shutdown(self) -> None:
        """Optional cleanup on shutdown."""