from pathlib import Path
from os import PathLike
from typing import Any, Dict, Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    PROJECT_NAME: str

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    DISCORD_OWNER: int
    DISCORD_TOKEN: str
    DISCORD_PREFIX: str
    DISCORD_PRIVACY_CHANNEL: int
    DISCORD_EMBED_COLOR: int

    CURRENT_STORY_CACHE: str

    GOOSEAI_TOKEN: Optional[str]
    SUKIMA_ENDPOINT: Optional[str]
    SUKIMA_USERNAME: Optional[str]
    SUKIMA_PASSWORD: Optional[str]

    DATABASE_URI: Optional[str] = None
    STORAGE_PATH: PathLike = Path.cwd() / "storage"

    @validator("DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return f"postgresql+asyncpg://{values.get('POSTGRES_USER')}:{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}/{values.get('POSTGRES_DB')}"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
