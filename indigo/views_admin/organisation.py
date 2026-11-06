"""The admin pages of organisations: which of the pages every type has organisations use, and the ones only organisations have."""
import csv

import jsonpointer
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from jsondataferret.models import Record, Type

import indigo.utils
from indigo import TYPE_ORGANISATION_PUBLIC_ID
from indigo.forms import (
    OrganisationEditForm,
    OrganisationImportForm,
    OrganisationNewForm,
)
from indigo.models import Organisation
from indigo.spreadsheetforms import (
    convert_organisation_data_to_spreadsheetforms_data,
    extract_edits_from_organisation_spreadsheet,
)
from indigo.views_admin.common import (
    DOWNLOAD_FORM_NOTE,
    permission_admin_or_data_steward_required,
    related_records_page,
)
from indigo.views_admin.generic.change_status import AdminModelChangeStatus
from indigo.views_admin.generic.downloads import (
    AdminModelDownloadBlankForm,
    AdminModelDownloadForm,
    form_downloads,
)
from indigo.views_admin.generic.edit import AdminModelEdit
from indigo.views_admin.generic.history import AdminModelHistory
from indigo.views_admin.generic.imports import AdminModelImportForm, read_spreadsheet
from indigo.views_admin.generic.lists import AdminModelList
from indigo.views_admin.generic.moderate import AdminModelModerate
from indigo.views_admin.generic.new import AdminModelNew
from indigo.views_admin.generic.records import AdminModelIndex


class AdminOrganisationList(AdminModelList):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _list_title = "Organisations"
    _noun_plural = "organisations"
    _add_label = "Organisation"
    _url_prefix = "organisation"
    _name_field = "data_private"
    _searchable = True
    _search_placeholder = "Name or ID"
    _search_extra_template = "indigo/admin/includes/organisation_goto.html"
    _menu_groups = [
        {
            "heading": "Spreadsheets",
            "items": [
                {
                    "label": "Download Blank Form",
                    "url_name": "indigo_admin_organisation_download_blank_form",
                },
                {
                    "label": "Download all as CSV",
                    "url_name": "indigo_admin_organisation_download_all_csv",
                },
            ],
        }
    ]

    def _get_items(self, request, search_term):
        organisations = Organisation.objects
        if search_term:
            organisations = organisations.filter(
                full_text_search_private__search=search_term
            )
        return organisations.order_by("public_id")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationIndex(AdminModelIndex):
    _model = Organisation
    _record_title = "Organisation"
    _list_title = "Organisations"
    _url_prefix = "organisation"
    _extra_actions = [
        ("Projects Using This", "indigo_admin_organisation_projects", True),
        ("Pipelines Using This", "indigo_admin_organisation_pipelines", True),
    ]
    _spreadsheets = form_downloads("organisation")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationNew(AdminModelNew):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _form_class = OrganisationNewForm
    _redirect_view = "indigo_admin_organisation_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationEdit(AdminModelEdit):
    _model = Organisation
    _record_title = "Organisation"
    _list_title = "Organisations"
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _form_class = OrganisationEditForm
    _redirect_view = "indigo_admin_organisation_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationChangeStatus(AdminModelChangeStatus):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _redirect_view = "indigo_admin_organisation_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationModerate(AdminModelModerate):
    _model = Organisation
    _redirect_view = "indigo_admin_organisation_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationHistory(AdminModelHistory):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationImportForm(AdminModelImportForm):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _form_class = OrganisationImportForm
    _redirect_view = "indigo_admin_organisation_index"

    def _get_import_json(self, file_path):
        # There are several versions of the organisation spreadsheet form, and we can read each of them
        versions = settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
            "spreadsheet_form_guide_spec_versions"
        ]
        version = indigo.utils.get_organisation_spreadsheet_version(file_path)
        if version not in versions.keys():
            raise Exception("This seems to not be a organisation spreadsheet?")
        return read_spreadsheet(versions[version], file_path)

    def _get_edits(self, data, import_json):
        return extract_edits_from_organisation_spreadsheet(data.record, import_json)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ORGANISATION_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminOrganisationDownloadForm(AdminModelDownloadForm):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ORGANISATION_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_organisation_data_to_spreadsheetforms_data(
            data, public_only=False
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


@permission_admin_or_data_steward_required()
def admin_organisations_goto(request):
    goto = request.POST.get("goto").strip()
    try:
        organisation = Organisation.objects.get(public_id=goto)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")

    return HttpResponseRedirect(
        reverse(
            "indigo_admin_organisation_index",
            kwargs={"public_id": organisation.public_id},
        )
    )


@permission_admin_or_data_steward_required()
def admin_organisations_search_json(request):
    """Used by the organisation picker on the edit forms. Either search by name, or look up by a comma separated list of IDs."""
    organisations = Organisation.objects.all()
    ids = [i.strip() for i in request.GET.get("ids", "").split(",") if i.strip()]
    search_term = request.GET.get("search", "").strip()
    if ids:
        organisations = organisations.filter(public_id__in=ids)
    elif search_term:
        organisations = organisations.filter(
            full_text_search_private__search=search_term
        )
    else:
        organisations = organisations.none()
    organisations = organisations.order_by("public_id")[:20]
    return JsonResponse(
        {
            "results": [
                {
                    "id": organisation.public_id,
                    "name": organisation.data_private.get("name", {}).get("value", ""),
                }
                for organisation in organisations
            ]
        }
    )


@permission_admin_or_data_steward_required()
def admin_organisation_download_all_csv(request):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    organisations = Record.objects.filter(type=type).order_by("public_id")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="organisations-admin.csv"'

    labels = ["ID"]
    keys = []

    for config in settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"]["fields"]:
        if config.get("type", "") != "list":
            labels.append(config.get("title"))
            keys.append(config.get("key"))

    writer = csv.writer(response)
    writer.writerow(labels)
    for organisation in organisations:
        row = [organisation.public_id]
        for key in keys:
            try:
                row.append(jsonpointer.resolve_pointer(organisation.cached_data, key))
            except jsonpointer.JsonPointerException:
                row.append("")
        writer.writerow(row)

    return response


@permission_required("indigo.admin")
def admin_organisation_projects(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return related_records_page(
        request,
        organisation,
        "Projects",
        "project",
        [
            link.project
            for link in organisation.included_by_projects.all()
            if link.in_current_data
        ],
    )


@permission_required("indigo.admin")
def admin_organisation_pipelines(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return related_records_page(
        request,
        organisation,
        "Pipelines",
        "pipeline",
        [
            link.pipeline
            for link in organisation.included_by_pipelines.all()
            if link.in_current_data
        ],
    )
