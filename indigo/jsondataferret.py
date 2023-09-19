from indigo.tasks import (
    task_after_fund_update,
    task_after_organisation_update,
    task_after_project_update,
)

from . import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from .updatedata import (
    update_assessment_resource,
    update_fund,
    update_joining_up_initiative,
    update_organisation,
    update_pipeline,
    update_project,
)


def on_update_callback(record):
    """This function may be called from within a transaction,
    and if the background task executes too quickly db records may not yet be in place.
    ( https://open-data-services.sentry.io/issues/4477948085/ when creating a project)
    Add a slight delay when calling background tasks as a hacky way to avoid"""
    if record.type.public_id == TYPE_PROJECT_PUBLIC_ID:
        update_project(
            record, update_include_organisations=True, update_include_funds=True
        )
        task_after_project_update.s(record.public_id).apply_async(countdown=2)
    elif record.type.public_id == TYPE_ORGANISATION_PUBLIC_ID:
        update_organisation(record, update_projects=True)
        task_after_organisation_update.s(record.public_id).apply_async(countdown=2)
    elif record.type.public_id == TYPE_FUND_PUBLIC_ID:
        update_fund(record, update_projects=True)
        task_after_fund_update.s(record.public_id).apply_async(countdown=2)
    elif record.type.public_id == TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID:
        update_assessment_resource(record)
    elif record.type.public_id == TYPE_PIPELINE_PUBLIC_ID:
        update_pipeline(record, update_include_organisations=True)
    elif record.type.public_id == TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID:
        update_joining_up_initiative(record)
