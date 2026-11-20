from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
_SQLITE_PATH = (ROOT / "backend" / "storyforge.db").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", Path(__file__).resolve().parents[1] / ".env"),
        extra="ignore",
    )

    database_url: str = f"sqlite+pysqlite:///{_SQLITE_PATH}"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 60


settings = Settings()
