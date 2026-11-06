"""The admin pages of pipelines: which of the pages every type has pipelines use, and the ones only pipelines have."""
from django.conf import settings

from indigo import TYPE_PIPELINE_PUBLIC_ID
from indigo.dataqualityreport import DataQualityReportForPipeline
from indigo.forms import PipelineEditForm, PipelineNewForm
from indigo.models import Pipeline, PipelineImport
from indigo.spreadsheetforms import (
    convert_pipeline_data_to_spreadsheetforms_data,
    extract_edits_from_pipeline_spreadsheet,
)
from indigo.tasks import task_process_imported_pipeline_file
from indigo.views_admin.common import DOWNLOAD_FORM_NOTE
from indigo.views_admin.generic.change_status import AdminModelChangeStatus
from indigo.views_admin.generic.data_quality import AdminModelDataQualityReport
from indigo.views_admin.generic.downloads import (
    AdminModelDownloadBlankForm,
    AdminModelDownloadForm,
    blank_form_menu,
    form_downloads,
)
from indigo.views_admin.generic.edit import AdminModelEdit
from indigo.views_admin.generic.history import AdminModelHistory
from indigo.views_admin.generic.imports import (
    AdminModelImportFormStage1Of2,
    AdminModelImportFormStage2Of2,
)
from indigo.views_admin.generic.lists import AdminModelList
from indigo.views_admin.generic.moderate import AdminModelModerate
from indigo.views_admin.generic.new import AdminModelNew
from indigo.views_admin.generic.records import AdminModelIndex


class AdminPipelineList(AdminModelList):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _search_keys = ["name", "alternative_names"]
    _list_title = "Pipelines"
    _noun_plural = "pipelines"
    _add_label = "Pipeline"
    _url_prefix = "pipeline"
    _menu_groups = blank_form_menu("indigo_admin_pipeline_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineIndex(AdminModelIndex):
    _model = Pipeline
    _record_title = "Pipeline"
    _list_title = "Pipelines"
    _url_prefix = "pipeline"
    _extra_actions = [
        ("Data Quality Report", "indigo_admin_pipeline_data_quality_report")
    ]
    _spreadsheets = form_downloads("pipeline")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineNew(AdminModelNew):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _form_class = PipelineNewForm
    _redirect_view = "indigo_admin_pipeline_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineEdit(AdminModelEdit):
    _model = Pipeline
    _record_title = "Pipeline"
    _list_title = "Pipelines"
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _form_class = PipelineEditForm
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineChangeStatus(AdminModelChangeStatus):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineModerate(AdminModelModerate):
    _model = Pipeline
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineHistory(AdminModelHistory):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineImportFormStage1Of2(AdminModelImportFormStage1Of2):
    _model = Pipeline
    _import_model = PipelineImport
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_import_form_stage_2"

    def _set_record_on_import_model(self, record, import_data):
        import_data.pipeline = Pipeline.objects.get(public_id=record.public_id)

    def _send_message_to_worker(self, import_data):
        task_process_imported_pipeline_file.delay(import_data.id)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineImportFormStage2Of2(AdminModelImportFormStage2Of2):
    _model = Pipeline
    _import_model = PipelineImport
    _dqr_class = DataQualityReportForPipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"

    def _check_record_and_import_are_linked(self, record, import_data):
        return record.public_id == import_data.pipeline.public_id

    def _get_edits(self, record, import_json):
        return extract_edits_from_pipeline_spreadsheet(record, import_json)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineDownloadForm(AdminModelDownloadForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_pipeline_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineDataQualityReport(AdminModelDataQualityReport):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _data_quality_report = DataQualityReportForPipeline

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
