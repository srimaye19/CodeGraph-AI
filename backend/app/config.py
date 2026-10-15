"""
Application configuration management using Pydantic Settings and dotenv.
Loads from .env safely across project root and backend working directories.
"""

from pathlib import Path
from typing import Optional
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> Optional[Path]:
    """Find .env file in current dir, parent dir, or project root."""
    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        env_path = parent / ".env"
        if env_path.is_file():
            return env_path
        # Also check backend subdirectory if in root
        backend_env = parent / "backend" / ".env"
        if backend_env.is_file():
            return backend_env
    # Default fallback to file location relative
    file_rel = Path(__file__).resolve().parent.parent.parent / ".env"
    if file_rel.is_file():
        return file_rel
    return None


ENV_FILE_PATH = find_env_file()


class Settings(BaseSettings):
    """Application configuration with validation and defaults."""
    
    # Neo4j Database Settings
    NEO4J_URI: str = Field(default="neo4j+s://your-instance.databases.neo4j.io")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="")
    NEO4J_DATABASE: str = Field(default="neo4j")
    
    # AI Review Settings
    AI_PROVIDER: str = Field(default="none")  # 'none', 'gemini', 'openai'
    AI_API_KEY: str = Field(default="")
    AI_MODEL: str = Field(default="gemini-1.5-flash")
    
    # Scanner & Limits
    MAX_UPLOAD_MB: int = Field(default=25)
    MAX_FILES_PER_SCAN: int = Field(default=500)
    HOST: str = Field(default="127.0.0.1")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH) if ENV_FILE_PATH else ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def is_neo4j_configured(self) -> bool:
        """Check if real Neo4j credentials have been configured."""
        if not self.NEO4J_URI or not self.NEO4J_PASSWORD:
            return False
        # Check against common placeholder values
        placeholders = [
            "your-instance",
            "your-neo4j-password-here",
            "your-instance-id",
            "password123-placeholder"
        ]
        if any(p in self.NEO4J_URI.lower() for p in placeholders):
            return False
        if any(p in self.NEO4J_PASSWORD.lower() for p in placeholders):
            return False
        return True

    @property
    def project_root(self) -> Path:
        """Resolve project root directory."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def frontend_dir(self) -> Path:
        """Resolve frontend static directory."""
        return self.project_root / "frontend"


settings = Settings()
