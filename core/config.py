from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


class LlmConfig(BaseSettings):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    max_tool_iterations: int = 20


class DatabaseConfig(BaseSettings):
    db_path: Path = BASE_DIR / "aiboy.db"


class Config(BaseSettings):
    """Configuration hierarchy:
    1. Environment variables (AIBOY_*)
    2. .env file
    3. Code defaults (here)
    """
    model_config = {"env_prefix": "AIBOY_", "env_nested_delimiter": "__"}

    assistant_name: str = "aiboy"
    timezone: str = "Europe/Berlin"
    data_dir: Path = BASE_DIR.expanduser()

    # Secrets come ONLY from env vars, never from config files!
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")

    llm: LlmConfig = LlmConfig()
    database: DatabaseConfig = DatabaseConfig()

    # Security
    sandbox_mode: str = "docker"  # "off" or "docker"

    def resolve_db_path(self) -> Path:
        return Path(self.database.db_path).expanduser()


def load_config() -> Config:
    """Load config from env vars and .env."""
    load_dotenv()  # load .env, but do NOT override
    return Config()
