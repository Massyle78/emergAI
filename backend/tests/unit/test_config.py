"""Tests for application configuration loading and validation."""

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettingsDefaults:
    def test_default_env(self):
        s = Settings(supabase_url="", supabase_anon_key="")
        assert s.app_env == "development"

    def test_default_port(self):
        s = Settings()
        assert s.backend_port == 8000

    def test_default_debug_false(self):
        s = Settings()
        assert s.app_debug is False

    def test_default_gemini_model(self):
        s = Settings()
        assert s.gemini_model == "gemini-2.5-pro"


class TestSettingsOverrides:
    def test_override_via_kwargs(self):
        s = Settings(app_env="production", backend_port=9000)
        assert s.app_env == "production"
        assert s.backend_port == 9000

    def test_override_debug(self):
        s = Settings(app_debug=True)
        assert s.app_debug is True


class TestSettingsValidation:
    def test_rejects_port_below_range(self):
        with pytest.raises(ValidationError):
            Settings(backend_port=0)

    def test_rejects_port_above_range(self):
        with pytest.raises(ValidationError):
            Settings(backend_port=70000)

    def test_rejects_zero_workers(self):
        with pytest.raises(ValidationError):
            Settings(backend_workers=0)

    def test_rejects_zero_video_size(self):
        with pytest.raises(ValidationError):
            Settings(max_video_size_mb=0)


class TestSettingsProperties:
    def test_cors_origins_parsing(self):
        s = Settings(allowed_origins="http://a.com, http://b.com")
        assert s.cors_origins == ["http://a.com", "http://b.com"]

    def test_cors_origins_single(self):
        s = Settings(allowed_origins="http://localhost:3000")
        assert s.cors_origins == ["http://localhost:3000"]

    def test_cors_origins_strips_whitespace(self):
        s = Settings(allowed_origins="  http://a.com , http://b.com  ")
        assert s.cors_origins == ["http://a.com", "http://b.com"]

    def test_is_production_true(self):
        s = Settings(app_env="production")
        assert s.is_production is True

    def test_is_production_false(self):
        s = Settings(app_env="development")
        assert s.is_production is False

    def test_video_types_list(self):
        s = Settings(allowed_video_types="video/webm,video/mp4")
        assert s.video_types_list == ["video/webm", "video/mp4"]

    def test_audio_types_list(self):
        s = Settings(allowed_audio_types="audio/webm, audio/wav")
        assert s.audio_types_list == ["audio/webm", "audio/wav"]

    def test_empty_origins_returns_empty_list(self):
        s = Settings(allowed_origins="")
        assert s.cors_origins == []
