"""
PitWall AI — Backend Configuration
Environment-based settings using pydantic-settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Falls back to defaults for local development.
    """

    # API
    app_name: str = "PitWall AI"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",  # React dev
        "http://localhost:8501",  # Streamlit
        "http://localhost:8000",  # FastAPI itself
    ]

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "pitwall_ai"
    db_user: str = "pitwall_user"
    db_password: str = ""

    # Paths
    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    model_dir: Path = Path(__file__).resolve().parents[2] / "data" / "ml" / "models"
    cache_dir: Path = Path(__file__).resolve().parents[2] / "data" / "cache"

    class Config:
        env_file = ".env"
        extra = "ignore"
        protected_namespaces = ()


settings = Settings()
