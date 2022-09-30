release: python manage.py migrate
web: gunicorn --max-requests 100 --max-requests-jitter 10 djangoproject.wsgi
worker: celery -A indigo worker --without-heartbeat --without-gossip --without-mingle
