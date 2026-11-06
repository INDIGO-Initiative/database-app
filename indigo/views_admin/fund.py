"""The admin pages of funds: which of the pages every type has funds use, and the ones only funds have."""
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import Http404

from indigo import TYPE_FUND_PUBLIC_ID
from indigo.forms import FundEditForm, FundNewForm, ModelImportForm
from indigo.models import Fund
from indigo.spreadsheetforms import (
    convert_fund_data_to_spreadsheetforms_data,
    extract_edits_from_fund_spreadsheet,
)
from indigo.views_admin.common import DOWNLOAD_FORM_NOTE, related_records_page
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


class AdminFundList(AdminModelList):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Funds"
    _noun_plural = "funds"
    _add_label = "Fund"
    _url_prefix = "fund"
    _menu_groups = blank_form_menu("indigo_admin_fund_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundIndex(AdminModelIndex):
    _model = Fund
    _record_title = "Fund"
    _list_title = "Funds"
    _url_prefix = "fund"
    _extra_actions = [("Projects Using This", "indigo_admin_fund_projects", True)]
    _spreadsheets = form_downloads("fund")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


@permission_required("indigo.admin")
def admin_fund_projects(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    return related_records_page(
        request,
        fund,
        "Projects",
        "project",
        [
            link.project
            for link in fund.included_by_projects.all()
            if link.in_current_data
        ],
    )


class AdminFundNew(AdminModelNew):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = FundNewForm
    _redirect_view = "indigo_admin_fund_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundEdit(AdminModelEdit):
    _model = Fund
    _record_title = "Fund"
    _list_title = "Funds"
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = FundEditForm
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundChangeStatus(AdminModelChangeStatus):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundModerate(AdminModelModerate):
    _model = Fund
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundHistory(AdminModelHistory):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundImportForm(AdminModelImportForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = ModelImportForm
    _redirect_view = "indigo_admin_fund_index"

    def _get_edits(self, data, import_json):
        return extract_edits_from_fund_spreadsheet(data.record, import_json)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundDownloadForm(AdminModelDownloadForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_fund_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")
