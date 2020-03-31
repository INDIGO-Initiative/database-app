import copy

import jsonpointer
from jsondataferret.models import Record, Type

from indigo import TYPE_PROJECT_FILTER_KEYS_LIST, TYPE_PROJECT_PUBLIC_ID
from indigo.models import Project


def update_all_data():

    try:
        type_project = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        for project in Record.objects.filter(type=type_project):
            update_project(project)
    except Type.DoesNotExist:
        pass


def update_project(record):

    try:
        project = Project.objects.get(public_id=record.public_id)
    except Project.DoesNotExist:
        project = Project()
        project.public_id = record.public_id

    # Exists
    project.exists = record.cached_exists
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    project.status_public = record.cached_exists and record_status == "public"
    # Public data
    project.data_public = (
        filter_values(record.cached_data, TYPE_PROJECT_FILTER_KEYS_LIST)
        if project.status_public
        else {}
    )
    # Private Data
    project.data_private = record.cached_data if record.cached_exists else {}
    # Finally, Save
    project.save()


def filter_values(data, keys):
    data = copy.deepcopy(data)

    # Remove Record Status
    jsonpointer.set_pointer(data, "/status", None)

    for key in keys:
        try:
            key_data = jsonpointer.resolve_pointer(data, key)
        except jsonpointer.JsonPointerException:
            # Data does not exist anyway, nothing to do!
            continue
        key_status = key_data.get("status", "") if isinstance(key_data, dict) else ""
        if isinstance(key_status, str) and key_status.strip().lower() == "public":
            # Remove Status key, it must be public, people don't need to see that.
            jsonpointer.set_pointer(data, key + "/status", None)
        else:
            # Remove all data!
            jsonpointer.set_pointer(data, key, None)

    return data
