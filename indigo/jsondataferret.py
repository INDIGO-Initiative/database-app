from indigo.tasks import (
    task_update_public_files_for_fund,
    task_update_public_files_for_organisation,
    task_update_public_files_for_project,
)

from . import TYPE_FUND_PUBLIC_ID, TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from .updatedata import update_fund, update_organisation, update_project


def on_update_callback(record):
    if record.type.public_id == TYPE_PROJECT_PUBLIC_ID:
        update_project(
            record, update_include_organisations=True, update_include_funds=True
        )
        task_update_public_files_for_project.delay(record.public_id)
    elif record.type.public_id == TYPE_ORGANISATION_PUBLIC_ID:
        update_organisation(record, update_projects=True)
        task_update_public_files_for_organisation.delay(record.public_id)
    elif record.type.public_id == TYPE_FUND_PUBLIC_ID:
        update_fund(record, update_projects=True)
        task_update_public_files_for_fund.delay(record.public_id)
