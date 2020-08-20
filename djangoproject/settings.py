"""
Django settings for djangoproject project.

Generated by 'django-admin startproject' using Django 3.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""
import json
import os

from spreadsheetforms.api import get_guide_spec

from .util import JsonSchemaProcessor

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "jsondataferret.apps.JsondataferretConfig",
    "indigo.apps.IndigoConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "indigo.middleware.TemplateContextMiddleware",
]

ROOT_URLCONF = "djangoproject.urls"

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

WSGI_APPLICATION = "djangoproject.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = "/static/"

LOGIN_REDIRECT_URL = "/app/"

# We disable MemoryFileUploadHandler - there is code in app that assumes all files are written to disk
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.TemporaryFileUploadHandler"]

JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT = "%Y-%m-%d"


with open(os.path.join(BASE_DIR, "indigo", "jsonschema", "project.json")) as fp:
    project_json_schema = json.load(fp)
project_json_processor = JsonSchemaProcessor(
    input_filename=os.path.join(BASE_DIR, "indigo", "jsonschema", "project.json")
)

with open(os.path.join(BASE_DIR, "indigo", "jsonschema", "organisation.json")) as fp:
    organisation_json_schema = json.load(fp)


with open(os.path.join(BASE_DIR, "indigo", "jsonschema", "fund.json")) as fp:
    fund_json_schema = json.load(fp)


_PROJECT_SPREADSHEET_FORM_GUIDE_FILENAME = os.path.join(
    BASE_DIR, "indigo", "spreadsheetform_guides", "project.xlsx",
)
_FUND_SPREADSHEET_FORM_GUIDE_FILENAME = os.path.join(
    BASE_DIR, "indigo", "spreadsheetform_guides", "fund.xlsx",
)
_ORGANISATION_SPREADSHEET_FORM_GUIDE_FILENAME = os.path.join(
    BASE_DIR, "indigo", "spreadsheetform_guides", "organisation.xlsx",
)

JSONDATAFERRET_TYPE_INFORMATION = {
    "project": {
        "json_schema": project_json_schema,
        "spreadsheet_form_guide": _PROJECT_SPREADSHEET_FORM_GUIDE_FILENAME,
        "spreadsheet_form_guide_spec": get_guide_spec(
            _PROJECT_SPREADSHEET_FORM_GUIDE_FILENAME
        ),
        "fields": project_json_processor.get_fields(),
        "filter_keys": project_json_processor.get_filter_keys(),
    },
    "organisation": {
        "json_schema": organisation_json_schema,
        "spreadsheet_form_guide": _ORGANISATION_SPREADSHEET_FORM_GUIDE_FILENAME,
        "spreadsheet_form_guide_spec": get_guide_spec(
            _ORGANISATION_SPREADSHEET_FORM_GUIDE_FILENAME
        ),
        "fields": [
            {"key": "/name/value", "title": "Name"},
            {"key": "/org-ids/company/value", "title": "ORG-Ids - company"},
            {"key": "/org-ids/charity/value", "title": "ORG-Ids - charity"},
            {"key": "/org-ids/other/value", "title": "ORG-Ids - other"},
            {"key": "/contact/name/value", "title": "Contact Name"},
            {"key": "/contact/email/value", "title": "Contact Email"},
            {"key": "/website/value", "title": "Website"},
            {"key": "/address/value", "title": "Address"},
            {"key": "/postcode/value", "title": "Postcode"},
            {"key": "/country/value", "title": "Country"},
        ],
    },
    "fund": {
        "json_schema": fund_json_schema,
        "spreadsheet_form_guide": _FUND_SPREADSHEET_FORM_GUIDE_FILENAME,
        "spreadsheet_form_guide_spec": get_guide_spec(
            _FUND_SPREADSHEET_FORM_GUIDE_FILENAME
        ),
        "fields": [
            {"key": "/name/value", "title": "Name"},
            {"key": "/identifier_scheme/value", "title": "Identifier Scheme"},
            {"key": "/identifier/value", "title": "Identifier"},
            {"key": "/organisation_ids/value", "title": "Organisation Id's"},
            {"key": "/country/value", "title": "Country"},
            {
                "type": "list",
                "key": "/organisations",
                "title": "Organisations",
                "fields": [{"key": "/organisation_id/value", "title": "ID"},],
            },
        ],
    },
}

APP_TITLE = os.getenv("APP_TITLE", "INDIGO")

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN, integrations=[DjangoIntegration()],
    )

if "ON_HEROKU" in os.environ:
    import django_heroku

    django_heroku.settings(locals())
    DEBUG = False


else:

    import environ

    env = environ.Env(  # set default values and casting
        # SECURITY WARNING: keep the secret key used in production secret!
        JSONDATAFERRET_SECRET_KEY=(
            str,
            "lz@kp-&z6grz#fp#*!mi6c4-mozm)1u6m$57j%v21#u9l#lnog",
        ),
        JSONDATAFERRET_DEBUG=(bool, True),
        JSONDATAFERRET_ALLOWED_HOSTS=(list, []),
        JSONDATAFERRET_DATABASE_NAME=(str, "app"),
        JSONDATAFERRET_DATABASE_USER=(str, "app"),
        JSONDATAFERRET_DATABASE_PASSWORD=(str, "password"),
        JSONDATAFERRET_DATABASE_HOST=(str, "localhost"),
    )

    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = env("JSONDATAFERRET_SECRET_KEY")

    # SECURITY WARNING: don't run with debug turned on in production!
    DEBUG = env("JSONDATAFERRET_DEBUG")

    ALLOWED_HOSTS = env("JSONDATAFERRET_ALLOWED_HOSTS")

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("JSONDATAFERRET_DATABASE_NAME"),
            "USER": env("JSONDATAFERRET_DATABASE_USER"),
            "PASSWORD": env("JSONDATAFERRET_DATABASE_PASSWORD"),
            "HOST": env("JSONDATAFERRET_DATABASE_HOST"),
        }
    }
