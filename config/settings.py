"""Configurações do projeto.

O ambiente é escolhido pela variável APP_ENV (development | production) no .env:
  - development -> SUPABASE_URL_DEV / SUPABASE_KEY_DEV  (pampa-zoonoses-dev)
  - production  -> SUPABASE_URL     / SUPABASE_KEY      (pampa-zoonoses)

A API não usa o banco do Django (sem models, sem auth, sem sessões): todos os
dados são lidos do Supabase em modo somente leitura.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import logging

for nome in ("hpack", "httpcore", "httpx"):
    logging.getLogger(nome).setLevel(logging.WARNING)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    return [
        item.strip() for item in os.getenv(name, default).split(",") if item.strip()
    ]


# --------------------------------------------------------------------------
# Ambiente
# --------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
if APP_ENV not in {"development", "production"}:
    raise ImproperlyConfigured("APP_ENV deve ser 'development' ou 'production'.")
IS_PRODUCTION = APP_ENV == "production"

# --------------------------------------------------------------------------
# Supabase (um par de variáveis por ambiente)
# --------------------------------------------------------------------------
_URL_VAR, _KEY_VAR = (
    ("SUPABASE_URL", "SUPABASE_KEY")
    if IS_PRODUCTION
    else ("SUPABASE_URL_DEV", "SUPABASE_KEY_DEV")
)
SUPABASE_URL = os.getenv(_URL_VAR, "").strip()
SUPABASE_KEY = os.getenv(_KEY_VAR, "").strip()
_missing = [n for n, v in ((_URL_VAR, SUPABASE_URL), (_KEY_VAR, SUPABASE_KEY)) if not v]
if _missing:
    raise ImproperlyConfigured(
        f"APP_ENV={APP_ENV}: defina {', '.join(_missing)} no arquivo .env."
    )

# --------------------------------------------------------------------------
# Django
# --------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "").strip()
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY é obrigatória em produção.")
    SECRET_KEY = "dev-only-insecure-key"

DEBUG = _env_bool("DJANGO_DEBUG", default=not IS_PRODUCTION)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = ["corsheaders", "rest_framework", "api", "drf_spectacular"]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {}  # nenhum banco local: os dados vêm do Supabase
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = False
USE_TZ = True

# Cache em memória (listas de filtros). Em produção com vários processos,
# troque por Redis/Memcached.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
LOOKUP_CACHE_SECONDS = 300

# --------------------------------------------------------------------------
# CORS (apenas leitura)
# --------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5000",
]
CORS_ALLOW_ALL_ORIGINS = (not IS_PRODUCTION) and not CORS_ALLOWED_ORIGINS
CORS_ALLOW_METHODS = ["GET", "HEAD", "OPTIONS"]

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": os.getenv("THROTTLE_RATE", "120/min")},
    "EXCEPTION_HANDLER": "api.exceptions.handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "DEBUG" if DEBUG else "INFO"},
}
