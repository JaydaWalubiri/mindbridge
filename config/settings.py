import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-change-before-deployment")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "care",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True, "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug", "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
if os.environ.get("POSTGRES_DB"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ.get("POSTGRES_USER", ""), "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"), "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "en-ke"
TIME_ZONE = "Africa/Nairobi"
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
if os.environ.get("DJANGO_SERVE_STATIC", "0") == "1":
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
# Enable only behind a trusted proxy which overwrites X-Forwarded-Proto.
if os.environ.get("DJANGO_TRUST_PROXY", "0") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if x.strip()]
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
TURN_WEBHOOK_SECRET = os.environ.get("TURN_WEBHOOK_SECRET", "")
TURN_API_TOKEN = os.environ.get("TURN_API_TOKEN", "")
TURN_TEMPLATE_NAMESPACE = os.environ.get("TURN_TEMPLATE_NAMESPACE", "")
TURN_CHECKIN_TEMPLATE_NAME = os.environ.get("TURN_CHECKIN_TEMPLATE_NAME", "")
TURN_SESSION_TEMPLATE_NAME = os.environ.get("TURN_SESSION_TEMPLATE_NAME", "")
TURN_TEMPLATE_LANGUAGE = os.environ.get("TURN_TEMPLATE_LANGUAGE", "en")
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_HTTPS_ONLY", "0") == "1"
SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

TURN_STAFF_TEMPLATE_NAME = os.environ.get("TURN_STAFF_TEMPLATE_NAME", "")
TURN_SUPPORT_TEMPLATE_NAME = os.environ.get("TURN_SUPPORT_TEMPLATE_NAME", "")
RISK_NEGATIVE_THRESHOLD = float(os.environ.get("RISK_NEGATIVE_THRESHOLD", "0.85"))
SENTIMENT_ENABLED = os.environ.get("SENTIMENT_ENABLED", "0") == "1"
SENTIMENT_RISK_ENABLED = os.environ.get("SENTIMENT_RISK_ENABLED", "0") == "1"
_local_sentiment = BASE_DIR / "models" / "sentiment"
_has_local_model = (_local_sentiment / "model.safetensors").is_file()
SENTIMENT_MODEL = os.environ.get("SENTIMENT_MODEL", str(_local_sentiment) if _has_local_model else "distilbert/distilbert-base-uncased-finetuned-sst-2-english")
SENTIMENT_REVISION = os.environ.get("SENTIMENT_REVISION", "ad03426e4637f04d64fb1a30717029ccd6cb7054988020475db52569a7796798" if _has_local_model else "714eb0fa89d2f80546fda750413ed43d93601a13")
CONVERSATION_ENABLED = os.environ.get("CONVERSATION_ENABLED", "0") == "1"
CONVERSATION_URL = os.environ.get("CONVERSATION_URL", "")
CONVERSATION_API_TOKEN = os.environ.get("CONVERSATION_API_TOKEN", "")
CONVERSATION_TIMEOUT = min(8.0, max(0.1, float(os.environ.get("CONVERSATION_TIMEOUT", "8"))))
_conversation_manifest = BASE_DIR / "model_server" / "candidate.json"
_conversation_source = ""
if _conversation_manifest.is_file():
    _candidate = json.loads(_conversation_manifest.read_text(encoding="utf-8"))
    _conversation_source = _candidate["adapter_repo"] + "@" + _candidate["adapter_revision"]
CONVERSATION_EXPECTED_SOURCE = os.environ.get("CONVERSATION_EXPECTED_SOURCE", _conversation_source)
