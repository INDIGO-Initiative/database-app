import os
import tempfile

import spreadsheetforms.api
from django.conf import settings

import indigo.utils
from indigo.celery import app
from indigo.files import (
    update_data_quality_report_file_for_all_projects,
    update_public_archive_files,
    update_public_files_for_fund,
    update_public_files_for_organisation,
    update_public_files_for_pipeline,
    update_public_files_for_project,
)
from indigo.models import Fund, Organisation, Pipeline, Project, ProjectImport
from indigo.updatedata import update_project_low_priority


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_process_imported_project_file(self, project_import_id):
    project_import = ProjectImport.objects.get(id=project_import_id)

    if not project_import:
        # This should be impossible!
        return False

    if project_import.data or project_import.file_not_valid:
        # This has already been done!
        return False

    try:
        # Save File to disk
        file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        file.write(project_import.file_data)
        filename = file.name
        file.close()

        # Check version
        version = indigo.utils.get_project_spreadsheet_version(filename)
        if (
            version
            not in settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
                "spreadsheet_form_guide_spec_versions"
            ].keys()
        ):
            project_import.file_not_valid = True
            project_import.file_data = None
            project_import.save()
            return False

        # Get JSON data
        json_data = spreadsheetforms.api.get_data_from_form_with_guide_spec(
            settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
                "spreadsheet_form_guide_spec_versions"
            ][version],
            filename,
            date_format=getattr(
                settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
            ),
        )

        # delete temp file
        os.remove(filename)

        # Write JSON data to database
        project_import.data = json_data
        project_import.file_data = None
        project_import.save()

        return True
    except Exception as e:
        project_import.exception = True
        project_import.file_data = None
        project_import.save()
        raise e


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_public_files_for_project(self, project_id):
    update_public_files_for_project(Project.objects.get(public_id=project_id))


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_data_quality_report_file_for_all_projects(self):
    update_data_quality_report_file_for_all_projects()


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_public_files_for_organisation(self, organisation_id):
    update_public_files_for_organisation(
        Organisation.objects.get(public_id=organisation_id)
    )


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_public_files_for_fund(self, fund_id):
    update_public_files_for_fund(Fund.objects.get(public_id=fund_id))


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_public_files_for_pipeline(self, pipeline_id):
    update_public_files_for_pipeline(Pipeline.objects.get(public_id=pipeline_id))


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_update_public_archive_files(self):
    update_public_archive_files()


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_after_project_update(self, project_id):
    project = Project.objects.get(public_id=project_id)
    update_project_low_priority(project.record)
    update_public_files_for_project(project)


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_after_organisation_update(self, organisation_id):
    organisation = Organisation.objects.get(public_id=organisation_id)
    update_public_files_for_organisation(organisation)


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_after_fund_update(self, fund_id):
    fund = Fund.objects.get(public_id=fund_id)
    update_public_files_for_fund(fund)
