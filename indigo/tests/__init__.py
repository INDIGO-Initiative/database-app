import atexit
import shutil
import tempfile

from django.conf import settings

from celery.app.task import Task

# Saving a record writes spreadsheets and other files to the default storage, which would otherwise be the current
# directory (a "public" folder in the project). Send them somewhere temporary instead.
_test_media_root = tempfile.mkdtemp(prefix="indigo-test-media-")
settings.MEDIA_ROOT = _test_media_root
atexit.register(shutil.rmtree, _test_media_root, ignore_errors=True)

# Tasks queued by the tests must not reach the real broker, or a running worker would pick them up and write files for
# the development database. So the tests queue nothing; they call the task functions directly if they need them.
Task.apply_async = lambda self, *args, **kwargs: None
