"""Configuración de JDM Empeños por entorno."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


class Config:
    """Configuración base."""

    APP_NAME = os.getenv("BUSINESS_NAME", "JDM Empeños")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    REMEMBER_COOKIE_DURATION = timedelta(
        days=_int(os.getenv("REMEMBER_COOKIE_DURATION_DAYS"), 7)
    )
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=_int(os.getenv("SESSION_INACTIVITY_MINUTES"), 30)
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.getenv("SESSION_COOKIE_SECURE"), False)

    LOGIN_MAX_ATTEMPTS = _int(os.getenv("LOGIN_MAX_ATTEMPTS"), 5)
    LOGIN_LOCKOUT_MINUTES = _int(os.getenv("LOGIN_LOCKOUT_MINUTES"), 15)
    SESSION_INACTIVITY_MINUTES = _int(os.getenv("SESSION_INACTIVITY_MINUTES"), 30)

    BUSINESS_CURRENCY = os.getenv("BUSINESS_CURRENCY", "DOP")
    BUSINESS_CURRENCY_SYMBOL = os.getenv("BUSINESS_CURRENCY_SYMBOL", "RD$")
    BUSINESS_TIMEZONE = os.getenv("BUSINESS_TIMEZONE", "America/Santo_Domingo")
    BUSINESS_LOCALE = os.getenv("BUSINESS_LOCALE", "es_DO")

    UPLOAD_FOLDER = str(BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads"))
    MAX_CONTENT_LENGTH = _int(os.getenv("MAX_CONTENT_LENGTH_MB"), 16) * 1024 * 1024
    ALLOWED_IMAGE_EXTENSIONS = set(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_IMAGE_EXTENSIONS", "jpg,jpeg,png,webp").split(",")
        if ext.strip()
    )

    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    BABEL_DEFAULT_LOCALE = "es"
    BABEL_DEFAULT_TIMEZONE = BUSINESS_TIMEZONE

    @staticmethod
    def init_database_uri(cls_obj: type["Config"]) -> None:
        database_url = (os.getenv("DATABASE_URL") or "").strip()
        # Ignorar valores vacíos o placeholders del entorno del sistema
        if database_url.lower() in {"", "null", "none", "undefined"}:
            database_url = ""

        if database_url:
            # Render / Heroku a veces entregan postgres://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            # Usar driver psycopg v3 con SQLAlchemy
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+psycopg://", 1
                )
            elif database_url.startswith("postgresql+psycopg2://"):
                database_url = database_url.replace(
                    "postgresql+psycopg2://", "postgresql+psycopg://", 1
                )
            cls_obj.SQLALCHEMY_DATABASE_URI = database_url
        else:
            instance_dir = BASE_DIR / "instance"
            instance_dir.mkdir(parents=True, exist_ok=True)
            db_path = (instance_dir / "jdm_empenos.db").resolve().as_posix()
            cls_obj.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"


class DevelopmentConfig(Config):
    DEBUG = True
    ENV_NAME = "development"


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    ENV_NAME = "testing"
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    ENV_NAME = "production"
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env_name: str | None = None) -> type[Config]:
    name = (env_name or os.getenv("FLASK_ENV") or "development").lower()
    config_cls = config_by_name.get(name, DevelopmentConfig)
    if name != "testing":
        Config.init_database_uri(config_cls)
    return config_cls