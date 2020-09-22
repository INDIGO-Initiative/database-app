import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djangoproject.settings")

app = Celery("djangoproject")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.update(
    # Add config from https://www.cloudamqp.com/docs/celery.html
    broker_pool_limit=1,  # Will decrease connection usage
    broker_heartbeat=None,  # We're using TCP keep-alive instead
    broker_connection_timeout=30,  # May require a long timeout due to Linux DNS timeouts etc
    result_backend=None,  # AMQP is not recommended as result backend as it creates thousands of queues
    event_queue_expires=60,  # Will delete all celeryev. queues without consumers after 1 minute.
    worker_prefetch_multiplier=1,  # Disable prefetching, it's causes problems and doesn't help performance
    # Settings we have tweaked
    worker_concurrency=1,  # Keep low to have low memory use. And we have 1 core on Heroku anyway, and we have few tasks.
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
