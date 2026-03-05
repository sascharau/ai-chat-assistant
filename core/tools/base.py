import abc
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Tool(abc.ABC):
    """Abstract base class for tools.

    Each tool defines:
    - name: Unique name
    - description: Description for the LLM
    - input_schema: JSON schema for the input
    - risk_level: Risk level
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique tool name."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Description for the LLM."""

    @property
    @abc.abstractmethod
    def input_schema(self) -> dict:
        """JSON schema for the tool input."""

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def definition(self) -> dict:
        """Tool definition in Anthropic format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abc.abstractmethod
    async def execute(self, input_data: dict[str, Any], *, chat_id: str) -> str:
        """Execute the tool and return the result as a string."""
        pass