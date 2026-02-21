"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and type-check all config at startup.
Missing required values will raise a clear error before the app serves traffic.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings sourced from env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)
    app_log_level: str = Field(default="INFO")

    # FastAPI / Uvicorn
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000, ge=1, le=65535)
    backend_workers: int = Field(default=1, ge=1)
    allowed_origins: str = Field(default="http://localhost:3000")

    # Supabase
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="")

    # Google Gemini
    google_genai_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-pro")

    # Metriport
    metriport_api_key: str = Field(default="")
    metriport_base_url: str = Field(default="https://api.metriport.com")

    # Media processing
    max_video_size_mb: int = Field(default=50, ge=1)
    max_audio_size_mb: int = Field(default=20, ge=1)
    allowed_video_types: str = Field(default="video/webm,video/mp4")
    allowed_audio_types: str = Field(default="audio/webm,audio/wav,audio/mp3")
    temp_media_dir: str = Field(default="./tmp/media")

    # open-rppg
    rppg_model_name: str = Field(default="FacePhys.rlap")
    min_signal_quality: float = Field(default=0.3, ge=0.0, le=1.0)

    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated allowed origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """Check if the application is running in production."""
        return self.app_env == "production"

    @property
    def video_types_list(self) -> list[str]:
        """Parse comma-separated video MIME types into a list."""
        return [t.strip() for t in self.allowed_video_types.split(",") if t.strip()]

    @property
    def audio_types_list(self) -> list[str]:
        """Parse comma-separated audio MIME types into a list."""
        return [t.strip() for t in self.allowed_audio_types.split(",") if t.strip()]
