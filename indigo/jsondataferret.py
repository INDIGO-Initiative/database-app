from . import TYPE_PROJECT_PUBLIC_ID
from .updatedata import update_project


def on_update_callback(record):
    if record.type.public_id == TYPE_PROJECT_PUBLIC_ID:
        update_project(record)
