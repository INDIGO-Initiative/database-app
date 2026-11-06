"""The admin pages of projects: which of the pages every type has projects use, and the ones only projects have."""
import urllib.parse

from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from indigo import TYPE_PROJECT_PUBLIC_ID
from indigo.dataqualityreport import (
    DataQualityReportForAllProjects,
    DataQualityReportForProject,
)
from indigo.forms import ProjectEditForm, ProjectNewForm
from indigo.listpages import paginate
from indigo.models import AdminUserHasPermissionsForProject, Project, ProjectImport
from indigo.recordpages import SECTION_GROUPS
from indigo.spreadsheetforms import (
    convert_project_data_to_spreadsheetforms_data,
    extract_edits_from_project_spreadsheet,
)
from indigo.tasks import task_process_imported_project_file
from indigo.utils import tidy_field_title
from indigo.views_admin.common import (
    DOWNLOAD_FORM_NOTE,
    ProjectAccessMixin,
    subpage_context,
    user_can_access_project,
)
from indigo.views_admin.generic.change_status import AdminModelChangeStatus
from indigo.views_admin.generic.data_quality import AdminModelDataQualityReport
from indigo.views_admin.generic.downloads import (
    AdminModelDownloadBlankForm,
    AdminModelDownloadForm,
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


class AdminProjectList(AdminModelList):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _list_title = "Projects"
    _noun_plural = "projects"
    _add_label = "Project"
    _url_prefix = "project"
    _name_field = "data_private"
    _searchable = True
    _search_placeholder = "Project ID or name"
    _menu_groups = [
        {
            "heading": None,
            "items": [
                {
                    "label": "Data Quality Report",
                    "url_name": "indigo_admin_all_projects_data_quality_report",
                    "admin_only": True,
                }
            ],
        },
        {
            "heading": "Spreadsheets",
            "items": [
                {
                    "label": "Download Blank Form",
                    "url_name": "indigo_admin_project_download_blank_form",
                },
                {
                    "label": "Download Blank Simple Form",
                    "url_name": "indigo_admin_project_download_blank_simple_form",
                },
            ],
        },
    ]

    def _get_items(self, request, search_term):
        # A data steward only lists the projects they have been given access to
        return Project.objects.filter_by_admin_user_can_access(
            request.user, search=search_term
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectIndex(ProjectAccessMixin, AdminModelIndex):
    _model = Project
    _record_title = "Project"
    _list_title = "Projects"
    _url_prefix = "project"
    _extra_actions = [
        ("Data Quality Report", "indigo_admin_project_data_quality_report"),
        ("Data Steward Users", "indigo_admin_project_admin_users", True),
    ]
    _spreadsheets = [
        ("Download Form", "indigo_admin_project_download_form"),
        ("Download Simple Form", "indigo_admin_project_download_simple_form"),
        ("Upload/Import Form", "indigo_admin_project_import_form"),
    ]
    _notes = [DOWNLOAD_FORM_NOTE, "Simple Form: only for use on new projects."]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectNew(AdminModelNew):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _form_class = ProjectNewForm
    _redirect_view = "indigo_admin_project_edit"

    def _after_create(self, request, public_id):
        # A data steward has to be given access to the project right away
        if request.user.has_perm("indigo.data_steward"):
            AdminUserHasPermissionsForProject.objects.create(
                user=request.user,
                project=Project.objects.get(public_id=public_id),
                permission_access=True,
            )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectEdit(AdminModelEdit):
    _model = Project
    _record_title = "Project"
    _list_title = "Projects"
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _form_class = ProjectEditForm
    _redirect_view = "indigo_admin_project_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectChangeStatus(AdminModelChangeStatus):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectModerate(ProjectAccessMixin, AdminModelModerate):
    _model = Project
    _redirect_view = "indigo_admin_project_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectHistory(ProjectAccessMixin, AdminModelHistory):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectImportFormStage1Of2(AdminModelImportFormStage1Of2):
    _model = Project
    _import_model = ProjectImport
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_import_form_stage_2"

    def _set_record_on_import_model(self, record, import_data):
        import_data.project = Project.objects.get(public_id=record.public_id)

    def _send_message_to_worker(self, import_data):
        task_process_imported_project_file.delay(import_data.id)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectImportFormStage2Of2(AdminModelImportFormStage2Of2):
    _model = Project
    _import_model = ProjectImport
    _dqr_class = DataQualityReportForProject
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"

    def _check_record_and_import_are_linked(self, record, import_data):
        return record.public_id == import_data.project.public_id

    def _get_edits(self, record, import_json):
        return extract_edits_from_project_spreadsheet(record, import_json)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDownloadBlankSimpleForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDownloadForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectDownloadSimpleForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


PRIORITY_DESCRIPTIONS = {
    0: "Wrong data: a value that is not allowed or in the wrong format, or an ID that does not exist",
    1: "Missing: the most important fields",
    2: "Missing: important fields",
    3: "Missing: the other fields",
}


def _priority_summary():
    """For each priority level, how many projects have problems at that level, and how many problems in all."""
    summary = [
        {
            "priority": p,
            "description": PRIORITY_DESCRIPTIONS[p],
            "projects": 0,
            "issues": 0,
        }
        for p in range(4)
    ]
    counts_for_each_project = Project.objects.filter(exists=True).values_list(
        "data_quality_report_counts_by_priority", flat=True
    )
    for counts in counts_for_each_project:
        for row in summary:
            n = (counts or {}).get(str(row["priority"]), 0)
            if n:
                row["projects"] += 1
                row["issues"] += n
    return summary


def _section_title_of(field):
    """The section of the project edit form a field is in."""
    for title, keys in SECTION_GROUPS.get(TYPE_PROJECT_PUBLIC_ID, []):
        if field["key"].split("/")[1] in keys:
            return title
    return "Other"


def _field_sections(fields_single, fields_list):
    """The fields there are statistics for, grouped into the sections of the project edit form: [{"title", "fields":
    [{"label", "url", "is_list"}]}]. A section with no fields is left out."""
    sections = {
        title: [] for title, _ in SECTION_GROUPS.get(TYPE_PROJECT_PUBLIC_ID, [])
    }
    sections["Other"] = []
    for fields, url_name, is_list in [
        (
            fields_single,
            "indigo_admin_all_projects_data_quality_report_field_single",
            False,
        ),
        (fields_list, "indigo_admin_all_projects_data_quality_report_field_list", True),
    ]:
        for field in fields:
            sections[_section_title_of(field)].append(
                {
                    "label": tidy_field_title(field["title"]),
                    "url": reverse(url_name)
                    + "?field="
                    + urllib.parse.quote(field["key"], safe=""),
                    "is_list": is_list,
                }
            )
    return [{"title": t, "fields": f} for t, f in sections.items() if f]


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report(request):
    data_quality_report = DataQualityReportForAllProjects()
    return render(
        request,
        "indigo/admin/projects_data_quality_report.html",
        {
            "priority_summary": _priority_summary(),
            "count_projects": Project.objects.filter(exists=True).count(),
            "count_public_projects": Project.objects.filter(status_public=True).count(),
            "sections": _field_sections(
                data_quality_report.get_possible_fields_for_single_field_statistics(),
                data_quality_report.get_possible_fields_for_list_field_statistics(),
            ),
        },
    )


def _field_statistics_page(
    request, fields, get_statistics, with_key, without_key, is_list
):
    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    matching = [i for i in fields if i.get("key") == field_path]
    if not matching:
        raise Http404("Field does not exist")
    field = matching[0]
    statistics = get_statistics(field)
    with_value = statistics[with_key]
    total = statistics["count_public_projects"]
    return render(
        request,
        "indigo/admin/projects_data_quality_report_field.html",
        {
            "field": field,
            "label": tidy_field_title(field["title"]),
            "section_title": _section_title_of(field),
            "is_list": is_list,
            "total": total,
            "with_value": with_value,
            "without_value": statistics[without_key],
            "percent_with_value": round(100 * with_value / total) if total else 0,
        },
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report_field_single(request):
    data_quality_report = DataQualityReportForAllProjects()
    return _field_statistics_page(
        request,
        data_quality_report.get_possible_fields_for_single_field_statistics(),
        data_quality_report.get_single_field_statistics_for_field,
        "count_public_projects_with_public_value",
        "count_public_projects_without_public_value",
        is_list=False,
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report_field_list(request):
    data_quality_report = DataQualityReportForAllProjects()
    return _field_statistics_page(
        request,
        data_quality_report.get_possible_fields_for_list_field_statistics(),
        data_quality_report.get_list_field_statistics_for_field,
        "count_public_projects_with_at_least_one_public_value",
        "count_public_projects_without_any_public_values",
        is_list=True,
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_list_projects_by_priority_highest(
    request, priority
):
    priority = int(priority)
    if priority < 0 or priority > 3:
        raise Http404("Priority does not exist")
    # Only the fields the page shows, so the (large) data of every project is not loaded
    rows = [
        {"public_id": public_id, "name": name, "count": counts.get(str(priority))}
        for public_id, name, counts in Project.objects.filter(exists=True)
        .order_by("public_id")
        .values_list(
            "public_id",
            "data_private__name__value",
            "data_quality_report_counts_by_priority",
        )
        if (counts or {}).get(str(priority), 0) > 0
    ]
    # Most problems first (the sort is stable, so projects with the same count stay in ID order)
    rows.sort(key=lambda row: row["count"], reverse=True)
    page_obj, pagination_get_params = paginate(request, rows)
    return render(
        request,
        "indigo/admin/projects_data_quality_report_list_projects_by_priority_highest.html",
        {
            "priority": priority,
            "description": PRIORITY_DESCRIPTIONS[priority],
            "page_obj": page_obj,
            "pagination_get_params": pagination_get_params,
        },
    )


class AdminProjectDataQualityReport(AdminModelDataQualityReport):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _data_quality_report = DataQualityReportForProject

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


@permission_required("indigo.admin")
def admin_project_admin_users(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Record does not exist")

    # Get data
    admin_users_permissions = AdminUserHasPermissionsForProject.objects.filter(
        project=project
    )
    admin_users_with_access = [
        p.user for p in admin_users_permissions if p.permission_access
    ]
    admin_users_to_add = [
        u
        for u in User.objects.all()
        if u.has_perm("indigo.data_steward")
        and not u.has_perm("indigo.admin")
        and u not in admin_users_with_access
    ]

    # Actions
    if request.POST.get("action") == "add":

        try:
            user = User.objects.get(id=request.POST.get("user"))
            try:
                admin_user_permission = AdminUserHasPermissionsForProject.objects.get(
                    project=project, user=user
                )
                admin_user_permission.permission_access = True
                admin_user_permission.save()
            except AdminUserHasPermissionsForProject.DoesNotExist:
                admin_user_permission = AdminUserHasPermissionsForProject()
                admin_user_permission.user = user
                admin_user_permission.project = project
                admin_user_permission.permission_access = True
                admin_user_permission.save()
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_admin_users",
                    kwargs={"public_id": project.public_id},
                )
            )
        except User.DoesNotExist:
            pass

    elif request.POST.get("action") == "remove":
        try:
            user = User.objects.get(id=request.POST.get("user"))
            try:
                admin_user_permission = AdminUserHasPermissionsForProject.objects.get(
                    project=project, user=user
                )
                admin_user_permission.permission_access = False
                admin_user_permission.save()
            except AdminUserHasPermissionsForProject.DoesNotExist:
                pass
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_admin_users",
                    kwargs={"public_id": project.public_id},
                )
            )
        except User.DoesNotExist:
            pass

    # View page
    return render(
        request,
        "indigo/admin/project/admin_users.html",
        subpage_context(
            project.record,
            admin_users_permissions=admin_users_permissions,
            admin_users_to_add=admin_users_to_add,
            admin_users_with_access=admin_users_with_access,
        ),
    )
