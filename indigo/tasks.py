import os
import tempfile

import spreadsheetforms.api
from django.conf import settings

import indigo.utils
from indigo import TYPE_PIPELINE_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.celery import app
from indigo.files import (
    update_data_quality_report_file_for_all_projects,
    update_public_archive_files,
    update_public_files_for_fund,
    update_public_files_for_organisation,
    update_public_files_for_pipeline,
    update_public_files_for_project,
)
from indigo.models import (
    Fund,
    Organisation,
    Pipeline,
    PipelineImport,
    Project,
    ProjectImport,
)
from indigo.updatedata import update_project_low_priority


def _task_process_imported_model_file(
    import_data, get_model_spreadsheet_version, type_id
):

    if import_data.data or import_data.file_not_valid:
        # This has already been done!
        return False

    try:
        # Save File to disk
        file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        file.write(import_data.file_data)
        filename = file.name
        file.close()

        # Check version
        version = get_model_spreadsheet_version(filename)
        if (
            version
            not in settings.JSONDATAFERRET_TYPE_INFORMATION[type_id][
                "spreadsheet_form_guide_spec_versions"
            ].keys()
        ):
            import_data.file_not_valid = True
            import_data.file_data = None
            import_data.save()
            return False

        # Get JSON data
        json_data = spreadsheetforms.api.get_data_from_form_with_guide_spec(
            settings.JSONDATAFERRET_TYPE_INFORMATION[type_id][
                "spreadsheet_form_guide_spec_versions"
            ][version],
            filename,
            date_format=getattr(
                settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
            ),
            missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
        )

        # delete temp file
        os.remove(filename)

        # Write JSON data to database
        import_data.data = json_data
        import_data.file_data = None
        import_data.save()

        return True
    except Exception as e:
        import_data.exception = True
        import_data.file_data = None
        import_data.save()
        raise e


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_process_imported_project_file(self, project_import_id):
    try:
        import_data = ProjectImport.objects.get(id=project_import_id)
    except ProjectImport.DoesNotExist:
        # This should be impossible!
        return False

    return _task_process_imported_model_file(
        import_data,
        indigo.utils.get_project_spreadsheet_version,
        TYPE_PROJECT_PUBLIC_ID,
    )


@app.task(bind=True, acks_late=True, acks_on_failure_or_timeout=False)
def task_process_imported_pipeline_file(self, pipeline_import_id):
    try:
        import_data = PipelineImport.objects.get(id=pipeline_import_id)
    except PipelineImport.DoesNotExist:
        # This should be impossible!
        return False

    return _task_process_imported_model_file(
        import_data,
        indigo.utils.get_pipeline_spreadsheet_version,
        TYPE_PIPELINE_PUBLIC_ID,
    )


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
