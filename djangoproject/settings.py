"""
Django settings for djangoproject project.

Generated by 'django-admin startproject' using Django 3.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

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

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("JSONDATAFERRET_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("JSONDATAFERRET_DEBUG")

ALLOWED_HOSTS = env("JSONDATAFERRET_ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("JSONDATAFERRET_DATABASE_NAME"),
        "USER": env("JSONDATAFERRET_DATABASE_USER"),
        "PASSWORD": env("JSONDATAFERRET_DATABASE_PASSWORD"),
        "HOST": env("JSONDATAFERRET_DATABASE_HOST"),
    }
}


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

# We disable MemoryFileUploadHandler - there is code in example app that assumes all files are written to disk
FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.TemporaryFileUploadHandler"]

JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT = "%Y-%m-%d"

JSONDATAFERRET_TYPE_INFORMATION = {
    "project": {
        "jsonschema_file": os.path.join(
            BASE_DIR, "indigo", "jsonschema", "project.json"
        ),
        "spreadsheet_form_guide": os.path.join(
            BASE_DIR, "indigo", "spreadsheetform_guides", "project.xlsx",
        ),
        "fields": [
            {"key": "/project_name/value", "title": "Project Name (value)"},
            {"key": "/project_name/source", "title": "Project Name (source)"},
            {"key": "/project_name/status", "title": "Project Name (status)"},
            {"key": "/fund_name/value", "title": "Fund Name (value)"},
            {"key": "/fund_name/source", "title": "Fund Name (source)"},
            {"key": "/fund_name/status", "title": "Fund Name (status)"},
            {"key": "/launch_date/value", "title": "Launch Date (value)"},
            {"key": "/launch_date/source", "title": "Launch Date (source)"},
            {"key": "/launch_date/status", "title": "Launch Date (status)"},
            {
                "type": "list",
                "key": "/outcomes",
                "title": "Outcomes",
                "fields": [
                    {"key": "/title", "title": "Outcome"},
                    {"key": "/definition", "title": "Definition"},
                    {"key": "/source", "title": "Source"},
                ],
            },
        ],
    },
}
