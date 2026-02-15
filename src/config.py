"""Pydantic settings from .env."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "llm_todo_bot"
    LLM_MODEL: str = "ollama/deepseek-r1:14b"
    LLM_BASE_URL: str | None = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1000
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60
    MAX_TASKS_PER_USER: int = 200
    MAX_TOOL_CALLS_PER_MESSAGE: int = 10
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_GATHER_TURNS: int = 3

    class Config:
        env_file = ".env"
