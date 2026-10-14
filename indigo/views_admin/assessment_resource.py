"""The admin pages of assessment resources: which of the pages every type has assessment resources use, and the ones only assessment resources have."""
from django.conf import settings

from indigo import TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
from indigo.forms import (
    AssessmentResourceEditForm,
    AssessmentResourceNewForm,
    ModelImportForm,
)
from indigo.models import AssessmentResource
from indigo.spreadsheetforms import (
    convert_assessment_resource_data_to_spreadsheetforms_data,
    extract_edits_from_assessment_resource_spreadsheet,
)
from indigo.views_admin.generic.change_status import AdminModelChangeStatus
from indigo.views_admin.generic.downloads import (
    AdminModelDownloadBlankForm,
    AdminModelDownloadForm,
    blank_form_menu,
    form_downloads,
)
from indigo.views_admin.generic.edit import AdminModelEdit
from indigo.views_admin.generic.history import AdminModelHistory
from indigo.views_admin.generic.imports import AdminModelImportForm
from indigo.views_admin.generic.lists import AdminModelList
from indigo.views_admin.generic.moderate import AdminModelModerate
from indigo.views_admin.generic.new import AdminModelNew
from indigo.views_admin.generic.records import AdminModelIndex


class AdminAssessmentResourceList(AdminModelList):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Assessment Resources"
    _noun_plural = "assessment resources"
    _add_label = "Assessment Resource"
    _url_prefix = "assessment_resource"
    _menu_groups = blank_form_menu(
        "indigo_admin_assessment_resource_download_blank_form"
    )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceIndex(AdminModelIndex):
    _model = AssessmentResource
    _record_title = "Assessment Resource"
    _list_title = "Assessment Resources"
    _url_prefix = "assessment_resource"
    _spreadsheets = form_downloads("assessment_resource")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceNew(AdminModelNew):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = AssessmentResourceNewForm
    _redirect_view = "indigo_admin_assessment_resource_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceEdit(AdminModelEdit):
    _model = AssessmentResource
    _record_title = "Assessment Resource"
    _list_title = "Assessment Resources"
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = AssessmentResourceEditForm
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceChangeStatus(AdminModelChangeStatus):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceModerate(AdminModelModerate):
    _model = AssessmentResource
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceHistory(AdminModelHistory):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceImportForm(AdminModelImportForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = ModelImportForm
    _redirect_view = "indigo_admin_assessment_resource_index"

    def _get_edits(self, data, import_json):
        return extract_edits_from_assessment_resource_spreadsheet(
            data.record, import_json
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceDownloadForm(AdminModelDownloadForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_assessment_resource_data_to_spreadsheetforms_data(
            data, public_only=False
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
