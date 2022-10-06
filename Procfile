release: python manage.py migrate
web: gunicorn --max-requests 500 --max-requests-jitter 50 djangoproject.wsgi
worker: celery -A indigo worker --without-heartbeat --without-gossip --without-mingle