# Copyright © 2026 Xander Chen. All rights reserved.
"""Local assignment settings. Configure through environment variables."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
# Persist a generated local key so fresh startup needs no interactive setup.
# Production deployments should supply DJANGO_SECRET_KEY explicitly.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    key_path = DATA_DIR / ".django-secret-key"
    try:
        with key_path.open("x", encoding="utf-8") as key_file:
            key_file.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    SECRET_KEY = key_path.read_text(encoding="utf-8").strip()



def cookie_suffix(port):
    """Cookies are shared by every port on a host, so a second local copy of the app would overwrite this one's login."""
    port = str(port or "8000").strip()
    return "" if port == "8000" or not port.isdigit() else f"_{port}"


SESSION_COOKIE_NAME = "sessionid" + cookie_suffix(os.environ.get("PORT"))
CSRF_COOKIE_NAME = "csrftoken" + cookie_suffix(os.environ.get("PORT"))
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]"
).split(",") if host.strip()]
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "django.contrib.admin",
    "accounts", "discovery", "groups", "notifications",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "config.middleware.TabSlotMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.PrivatePagesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": DATA_DIR / "db.sqlite3",
    "OPTIONS": {"timeout": 20, "transaction_mode": "IMMEDIATE"},
}}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = DATA_DIR / "static"
STATICFILES_DIRS = [BASE_DIR / "static"]
LOGIN_URL = "login"
# What the profile calls the section holding event cards and achievements. Change this one word to rename it.
COLLECTION_NAME = "Collection"
LOGIN_REDIRECT_URL = "profile"
LOGOUT_REDIRECT_URL = "home"
# Browser tile requests retain an origin Referer, as required by OSM's tile policy.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
MEDIA_ROOT = DATA_DIR / "media"
# No raw public media route: processed group photos use a visibility-checked view.
MEDIA_URL = "/media/"
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
