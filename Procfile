release: python manage.py migrate
web: gunicorn djangoproject.wsgi
worker: celery --without-heartbeat -A indigo worker -l info
