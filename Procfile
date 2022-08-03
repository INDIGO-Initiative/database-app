release: python manage.py migrate
web: gunicorn djangoproject.wsgi
worker: celery -A indigo worker --without-heartbeat --without-gossip --without-mingle