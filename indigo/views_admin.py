import csv
import datetime
import os
import random
import tempfile
import urllib.parse
from abc import ABC

import jsondataferret
import jsondataferret.utils
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models.functions import Now
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from jsondataferret.models import CachedRecordHistory, Edit, Event, Record, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.processdata
import indigo.utils
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.dataqualityreport import (
    DataQualityReportForAllProjects,
    DataQualityReportForPipeline,
    DataQualityReportForProject,
)
from indigo.filters import HistoryFilter
from indigo.listpages import list_context, paginate, search_filter, visible_menu
from indigo.recordpages import build_record_sections
from indigo.tasks import (
    task_process_imported_pipeline_file,
    task_process_imported_project_file,
)

from .forms import (
    AssessmentResourceEditForm,
    AssessmentResourceNewForm,
    FundEditForm,
    FundNewForm,
    JoiningUpInitiativeEditForm,
    JoiningUpInitiativeNewForm,
    ModelImportForm,
    ModelImportStage1Of2Form,
    ModelImportStage2Of2Form,
    OrganisationImportForm,
    OrganisationNewForm,
    PipelineEditForm,
    PipelineNewForm,
    ProjectEditForm,
    ProjectNewForm,
    RecordChangeStatusForm,
    OrganisationEditForm,
)
from .models import (
    AdminUserHasPermissionsForProject,
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    PipelineImport,
    Project,
    ProjectImport,
    Sandbox,
)
from .spreadsheetforms import (
    convert_assessment_resource_data_to_spreadsheetforms_data,
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_pipeline_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
    extract_edits_from_assessment_resource_spreadsheet,
    extract_edits_from_form,
    extract_edits_from_fund_spreadsheet,
    extract_edits_from_organisation_spreadsheet,
    extract_edits_from_pipeline_spreadsheet,
    extract_edits_from_project_spreadsheet,
)


RECORD_TITLES = {
    TYPE_PROJECT_PUBLIC_ID: ("Project", "Projects"),
    TYPE_ORGANISATION_PUBLIC_ID: ("Organisation", "Organisations"),
    TYPE_FUND_PUBLIC_ID: ("Fund", "Funds"),
    TYPE_PIPELINE_PUBLIC_ID: ("Pipeline", "Pipelines"),
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID: ("Assessment Resource", "Assessment Resources"),
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID: (
        "Joining Up Initiative",
        "Joining Up Initiatives",
    ),
}


def _list_context_for_type(type_public_id):
    """What the pages of a type's records need to link back to the type's list (type ids are also the URL prefixes)."""
    record_title, list_title = RECORD_TITLES[type_public_id]
    return {
        "record_title": record_title,
        "list_title": list_title,
        "list_url": reverse(f"indigo_admin_{type_public_id}_list"),
    }


def _new_page(request, type_public_id, form, full_form=False):
    """The page for adding a record: just a name to start with, or (full_form) the whole record in one go."""
    context = _list_context_for_type(type_public_id)
    context.update({"form": form, "full_form": full_form})
    return render(request, "indigo/admin/new.html", context)


def _subpage_context(record, **extra):
    """The context of a page about one record (change status, history...): see admin/record_subpage.html."""
    type_public_id = record.type.public_id
    data = (record.cached_data if record.cached_exists else None) or {}
    name = data.get("name")
    context = _list_context_for_type(type_public_id)
    context.update(
        {
            "record": record,
            "record_url": reverse(
                f"indigo_admin_{type_public_id}_index",
                kwargs={"public_id": record.public_id},
            ),
            "display_name": name.get("value", "") if isinstance(name, dict) else "",
        }
    )
    context.update(extra)
    return context


def _related_records_page(
    request, model_instance, related_title, related_noun, related_records
):
    """A page listing the records of another type that link to this one, eg the projects using an organisation."""
    links = [
        {
            "public_id": related.public_id,
            "name": ((related.data_private or {}).get("name") or {}).get("value", ""),
            "url": reverse(
                f"indigo_admin_{related.record.type.public_id}_index",
                kwargs={"public_id": related.public_id},
            ),
        }
        for related in related_records
    ]
    return render(
        request,
        "indigo/admin/related_records.html",
        _subpage_context(
            model_instance.record,
            related_title=related_title,
            related_noun=related_noun,
            links=links,
        ),
    )


def _record_history_page(request, record):
    page_obj, pagination_get_params = paginate(
        request, _events_for_record_newest_first(record)
    )
    return render(
        request,
        "indigo/admin/record_history.html",
        _subpage_context(
            record, page_obj=page_obj, pagination_get_params=pagination_get_params
        ),
    )


def _events_for_record_newest_first(record):
    """The events that changed a record (or tried to), latest first.

    (jsondataferret gives them oldest first, so we turn them round.)"""
    return sorted(
        Event.objects.filter_by_record(record),
        key=lambda event: (event.created, event.id),
        reverse=True,
    )


def _edit_changes(edit, record):
    """What approving this edit would change on the record, as a list of
    {"title", "old", "new", "kind"} where kind is "added", "changed" or "removed".

    Only fields that differ are included, so a big edit that mostly repeats the current data is still easy to read."""
    type_public_id = record.type.public_id
    get_fields = jsondataferret.utils.get_field_list_from_json
    old_fields = {
        f["key"]: f
        for f in get_fields(
            type_public_id, record.cached_data if record.cached_exists else {}
        )
    }
    new_fields = {
        f["key"]: f
        for f in get_fields(
            type_public_id,
            edit.get_new_data_when_edit_applied_to_latest_record_cached_data(),
        )
    }
    changes = []
    for key, field in new_fields.items():
        old = old_fields.get(key)
        if old is None:
            changes.append(
                {
                    "title": indigo.utils.tidy_field_title(field["title"]),
                    "old": None,
                    "new": field["value"],
                    "kind": "added",
                }
            )
        elif old["value"] != field["value"]:
            changes.append(
                {
                    "title": indigo.utils.tidy_field_title(field["title"]),
                    "old": old["value"],
                    "new": field["value"],
                    "kind": "changed",
                }
            )
    for key, field in old_fields.items():
        if key not in new_fields:
            changes.append(
                {
                    "title": indigo.utils.tidy_field_title(field["title"]),
                    "old": field["value"],
                    "new": None,
                    "kind": "removed",
                }
            )
    return changes


def _add_moderation_message(request, actions):
    approved = len(
        [
            a
            for a in actions
            if isinstance(a, jsondataferret.pythonapi.newevent.NewEventApproval)
        ]
    )
    rejected = len(actions) - approved
    parts = []
    if approved:
        parts.append(f"{approved} approved")
    if rejected:
        parts.append(f"{rejected} rejected")
    messages.add_message(
        request, messages.INFO, "Moderation saved: " + ", ".join(parts) + "."
    )


DOWNLOAD_FORM_NOTE = "You can delete any sheet/tab from a downloaded form (except the introduction one) and it will still work fine."


def _admin_record_page(
    request,
    record,
    *,
    record_title,
    type_public_id,
    url_prefix,
    list_title,
    extra_actions=(),
    spreadsheets=(),
    notes=(),
):
    """The admin page of one record: its fields in sections, with an Edit button and a More menu.

    extra_actions are (label, url name, admin only?) for this type's own pages. spreadsheets are (label, url name),
    which all need the record's ID."""
    kwargs = {"public_id": record.public_id}

    def item(label, url_name, admin_only=False):
        return {
            "label": label,
            "url_name": url_name,
            "url_kwargs": kwargs,
            "admin_only": admin_only,
        }

    groups = [
        {
            "heading": None,
            "items": [
                item("Change Status", f"indigo_admin_{url_prefix}_change_status"),
                item("Moderate", f"indigo_admin_{url_prefix}_moderate"),
                item("History", f"indigo_admin_{url_prefix}_history"),
            ]
            + [item(*action) for action in extra_actions],
        }
    ]
    if spreadsheets:
        groups.append(
            {
                "heading": "Spreadsheets",
                "items": [item(*s) for s in spreadsheets],
                "notes": list(notes),
            }
        )
    name = (record.data_private or {}).get("name")
    return render(
        request,
        "indigo/admin/record.html",
        {
            "record": record,
            "record_title": record_title,
            "display_name": name.get("value", "") if isinstance(name, dict) else "",
            "sections": build_record_sections(type_public_id, record.data_private),
            "edit_url": reverse(f"indigo_admin_{url_prefix}_edit", kwargs=kwargs),
            "menu": visible_menu(request.user, groups),
            "list_title": list_title,
            "list_url": reverse(f"indigo_admin_{url_prefix}_list"),
        },
    )


def _permission_admin_or_data_steward_required_test(user):
    return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


def permission_admin_or_data_steward_required():
    return user_passes_test(_permission_admin_or_data_steward_required_test)


def user_can_access_project(user, project: Project):
    # Must be a user
    if not user:
        return False
    # Admin
    if user.has_perm("indigo.admin"):
        return True
    # Data Steward that has access to this project?
    if user.has_perm("indigo.data_steward"):
        try:
            admin_user_permission = AdminUserHasPermissionsForProject.objects.get(
                project=project, user=user
            )
            if admin_user_permission.permission_access:
                return True
        except AdminUserHasPermissionsForProject.DoesNotExist:
            pass
    # Then No
    return False


def user_can_access_event(user, event: Event):
    # Must be a user
    if not user:
        return False
    # Admin
    if user.has_perm("indigo.admin"):
        return True
    # Data Steward that has access to a single edit for this event?
    if user.has_perm("indigo.data_steward"):
        for edit in event.edits_created.all():
            if user_can_access_edit(user, edit):
                return True
        for edit in event.edits_approved.all():
            if user_can_access_edit(user, edit):
                return True
        for edit in event.edits_refused.all():
            if user_can_access_edit(user, edit):
                return True
    # Then No
    return False


def user_can_access_edit(user, edit: Edit):
    # Must be a user
    if not user:
        return False
    # Admin
    if user.has_perm("indigo.admin"):
        return True
    # Data Steward that has access to the data the edit is about?
    if user.has_perm("indigo.data_steward"):
        if edit.record.type.public_id in [
            TYPE_FUND_PUBLIC_ID,
            TYPE_ORGANISATION_PUBLIC_ID,
        ]:
            return True
        elif edit.record.type.public_id == TYPE_PROJECT_PUBLIC_ID:
            try:
                admin_user_permission = AdminUserHasPermissionsForProject.objects.get(
                    project=Project.objects.get(public_id=edit.record.public_id),
                    user=user,
                )
                if admin_user_permission.permission_access:
                    return True
            except AdminUserHasPermissionsForProject.DoesNotExist:
                pass
    # Then No
    return False


def _count_records_needing_moderation(type_public_id):
    try:
        type = Type.objects.get(public_id=type_public_id)
    except Type.DoesNotExist:
        return 0
    return len(list(Record.objects.filter_needs_moderation_by_type(type)))


@permission_admin_or_data_steward_required()
def admin_index(request):
    user = request.user
    is_admin = user.has_perm("indigo.admin")

    # The "To Moderate" page is for admins, so only admins are told what is waiting
    def waiting(type_public_id):
        return _count_records_needing_moderation(type_public_id) if is_admin else None

    sections = [
        {
            "title": "Projects",
            "icon": "diagram-project",
            "count": Project.objects.filter_by_admin_user_can_access(user).count(),
            "waiting": waiting(TYPE_PROJECT_PUBLIC_ID),
            "list_url": "indigo_admin_project_list",
            "new_url": "indigo_admin_project_new",
        },
        {
            "title": "Organisations",
            "icon": "building",
            "count": Organisation.objects.count(),
            "waiting": waiting(TYPE_ORGANISATION_PUBLIC_ID),
            "list_url": "indigo_admin_organisation_list",
            "new_url": "indigo_admin_organisation_new",
        },
        {
            "title": "Funds",
            "icon": "coins",
            "count": Fund.objects.count(),
            "waiting": waiting(TYPE_FUND_PUBLIC_ID),
            "list_url": "indigo_admin_fund_list",
            "new_url": "indigo_admin_fund_new",
        },
    ]
    if is_admin:
        sections += [
            {
                "title": "Pipelines",
                "icon": "bars-progress",
                "count": Pipeline.objects.count(),
                "waiting": waiting(TYPE_PIPELINE_PUBLIC_ID),
                "list_url": "indigo_admin_pipeline_list",
                "new_url": "indigo_admin_pipeline_new",
            },
            {
                "title": "Assessment Resources",
                "icon": "clipboard-check",
                "count": AssessmentResource.objects.count(),
                "waiting": waiting(TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID),
                "list_url": "indigo_admin_assessment_resource_list",
                "new_url": "indigo_admin_assessment_resource_new",
            },
            {
                "title": "Joining Up Initiatives",
                "icon": "handshake",
                "count": JoiningUpInitiative.objects.count(),
                "waiting": waiting(TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID),
                "list_url": "indigo_admin_joining_up_initiative_list",
                "new_url": "indigo_admin_joining_up_initiative_new",
            },
        ]
    return render(
        request,
        "indigo/admin/index.html",
        {
            "sections": sections,
            "waiting_total": sum(s["waiting"] or 0 for s in sections)
            if is_admin
            else None,
            "sandbox_count": Sandbox.objects.count(),
        },
    )


def _admin_links_to_records_of(event):
    """The records an event is about, as links to their admin pages: [{"label", "url"}], and whether there are more.

    A record of a type with no admin page has no url, so it is shown as plain text.
    (get_records_summary gives Record objects that also have type_public_id and type_title.)"""
    summary = event.get_records_summary()
    links = []
    for record in summary["records"]:
        try:
            url = reverse(
                f"indigo_admin_{record.type_public_id}_index",
                kwargs={"public_id": record.public_id},
            )
        except NoReverseMatch:
            url = None
        links.append({"label": f"{record.type_title}: {record.public_id}", "url": url})
    return links, bool(summary["more"])


def _history_quick_ranges():
    today = timezone.localdate()

    def link(label, days_back):
        query = urllib.parse.urlencode(
            {
                "created__gt": (today - datetime.timedelta(days=days_back)).isoformat(),
                "created__lt": today.isoformat(),
            }
        )
        return {"label": label, "url": f"{reverse('indigo_admin_history')}?{query}"}

    return [link("Today", 0), link("Last 7 days", 6), link("Last 30 days", 29)]


@permission_required("indigo.admin")
def admin_history(request):
    filter = HistoryFilter(
        request.GET, queryset=Event.objects.all().order_by("-created", "-id")
    )
    page_obj, pagination_get_params = paginate(request, filter.qs)
    for event in page_obj:
        event.record_links, event.more_records = _admin_links_to_records_of(event)
    return render(
        request,
        "indigo/admin/history.html",
        {
            "page_obj": page_obj,
            "filter": filter,
            "pagination_get_params": pagination_get_params,
            "filtered": any(request.GET.get(k) for k in ("created__gt", "created__lt")),
            "quick_ranges": _history_quick_ranges(),
        },
    )


########################### Admin - Projects


@permission_admin_or_data_steward_required()
def admin_projects_list(request):
    search_term = request.GET.get("search", "").strip()
    projects = Project.objects.filter_by_admin_user_can_access(
        request.user, search=search_term
    )
    return render(
        request,
        "indigo/admin/list.html",
        list_context(
            request,
            projects,
            title="Projects",
            noun_plural="projects",
            name_field="data_private",
            index_url_name="indigo_admin_project_index",
            list_url_name="indigo_admin_project_list",
            items_key="projects",
            search_term=search_term,
            searchable=True,
            search_placeholder="Project ID or name",
            edit_url_name="indigo_admin_project_edit",
            add_url_name="indigo_admin_project_new",
            add_label="Project",
            menu_groups=[
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
            ],
        ),
    )


@permission_admin_or_data_steward_required()
def admin_project_index(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    if not user_can_access_project(request.user, project):
        raise PermissionDenied("You can not see project")
    return _admin_record_page(
        request,
        project,
        record_title="Project",
        type_public_id=TYPE_PROJECT_PUBLIC_ID,
        url_prefix="project",
        list_title="Projects",
        extra_actions=[
            ("Data Quality Report", "indigo_admin_project_data_quality_report"),
            ("Data Steward Users", "indigo_admin_project_admin_users", True),
        ],
        spreadsheets=[
            ("Download Form", "indigo_admin_project_download_form"),
            ("Download Simple Form", "indigo_admin_project_download_simple_form"),
            ("Upload/Import Form", "indigo_admin_project_import_form"),
        ],
        notes=[DOWNLOAD_FORM_NOTE, "Simple Form: only for use on new projects."],
    )


@permission_admin_or_data_steward_required()
@transaction.atomic
def admin_projects_new(request):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")

    # If this is a POST request then process the Form data
    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectNewForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = indigo.utils.get_next_record_id(type)
            data = NewEventData(
                type,
                id,
                {"name": {"value": form.cleaned_data["name"]}},
                approved=True,
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            # If user is a data steward, have to give them access to project right away
            if request.user.has_perm("indigo.data_steward"):
                p = AdminUserHasPermissionsForProject()
                p.user = request.user
                p.project = Project.objects.get(public_id=id)
                p.permission_access = True
                p.save()

            messages.add_message(
                request,
                messages.INFO,
                "Created. Now fill in the rest of the details; they will be available once they have been moderated.",
            )

            # redirect to the edit form
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_edit",
                    kwargs={"public_id": id},
                )
            )

    # If this is a GET (or any other method) create the default form.
    else:
        form = ProjectNewForm()

    return _new_page(request, TYPE_PROJECT_PUBLIC_ID, form)


@permission_admin_or_data_steward_required()
def admin_project_moderate(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Record does not exist")
    record = project.record
    if not user_can_access_project(request.user, project):
        raise PermissionDenied("You can not see project")

    edits = Edit.objects.filter(record=record, approval_event=None, refusal_event=None)

    if request.method == "POST" and request.user.has_perm("indigo.admin"):

        # TODO check CSFR

        actions = []
        for edit in edits:
            action = request.POST.get("action_" + str(edit.id))
            if action == "approve":
                actions.append(jsondataferret.pythonapi.newevent.NewEventApproval(edit))
            elif action == "reject":
                actions.append(
                    jsondataferret.pythonapi.newevent.NewEventRejection(edit)
                )

        if actions:
            jsondataferret.pythonapi.newevent.newEvent(
                actions, user=request.user, comment=request.POST.get("comment")
            )
            _add_moderation_message(request, actions)

        return HttpResponseRedirect(
            reverse(
                "indigo_admin_project_index",
                kwargs={"public_id": public_id},
            )
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.changes = _edit_changes(edit, record)

    return render(
        request,
        "indigo/admin/moderate.html",
        _subpage_context(record, edits=edits),
    )


@permission_admin_or_data_steward_required()
def admin_project_history(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Record does not exist")
    record = project.record
    if not user_can_access_project(request.user, project):
        raise PermissionDenied("You can not see project")

    return _record_history_page(request, record)


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
        _subpage_context(
            project.record,
            admin_users_permissions=admin_users_permissions,
            admin_users_to_add=admin_users_to_add,
            admin_users_with_access=admin_users_with_access,
        ),
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report(request):
    data_quality_report = DataQualityReportForAllProjects()
    return render(
        request,
        "indigo/admin/projects_data_quality_report.html",
        {
            "fields_single": data_quality_report.get_possible_fields_for_single_field_statistics(),
            "fields_list": data_quality_report.get_possible_fields_for_list_field_statistics(),
        },
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report_field_single(request):

    data_quality_report = DataQualityReportForAllProjects()

    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    fields = [
        i
        for i in data_quality_report.get_possible_fields_for_single_field_statistics()
        if i.get("key") == field_path
    ]
    if not fields:
        raise Http404("Field does not exist")  #
    field = fields[0]

    data = {"field": field}
    data.update(data_quality_report.get_single_field_statistics_for_field(field))

    return render(
        request,
        "indigo/admin/projects_data_quality_report_single_field.html",
        data,
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report_field_list(request):

    data_quality_report = DataQualityReportForAllProjects()

    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    fields = [
        i
        for i in data_quality_report.get_possible_fields_for_list_field_statistics()
        if i.get("key") == field_path
    ]
    if not fields:
        raise Http404("Field does not exist")  #
    field = fields[0]

    data = {"field": field}
    data.update(data_quality_report.get_list_field_statistics_for_field(field))

    return render(
        request,
        "indigo/admin/projects_data_quality_report_list_field.html",
        data,
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_list_projects_by_priority_highest(
    request, priority
):
    priority = int(priority)
    if priority < 0 or priority > 3:
        raise Http404("Priority does not exist")
    projects = Project.objects.filter(exists=True)
    projects = [
        p
        for p in projects
        if p.data_quality_report_counts_by_priority.get(str(priority), 0) > 0
    ]
    projects = sorted(
        projects,
        key=lambda x: x.data_quality_report_counts_by_priority.get(str(priority)),
        reverse=True,
    )
    return render(
        request,
        "indigo/admin/projects_data_quality_report_list_projects_by_priority_highest.html",
        {
            "priority": priority,
            "projects_with_count": [
                (
                    project,
                    project.data_quality_report_counts_by_priority.get(str(priority)),
                )
                for project in projects
            ],
        },
    )


########################### Admin - Organisations


@permission_admin_or_data_steward_required()
def admin_organisation_download_blank_form(request):
    type_data = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ORGANISATION_PUBLIC_ID, {}
    )
    if not type_data.get("spreadsheet_form_guide"):
        raise Http404("Feature not available")

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    spreadsheetforms.api.make_empty_form(
        type_data.get("spreadsheet_form_guide"), out_file
    )

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=organisation.xlsx"

    return response


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
def admin_organisations_search(request):
    search_term = request.GET.get("search", "").strip()
    organisations = Organisation.objects
    if search_term:
        organisations = organisations.filter(
            full_text_search_private__search=search_term
        )
    organisations = organisations.order_by("public_id")
    return render(
        request,
        "indigo/admin/list.html",
        list_context(
            request,
            organisations,
            title="Organisations",
            noun_plural="organisations",
            name_field="data_private",
            index_url_name="indigo_admin_organisation_index",
            list_url_name="indigo_admin_organisation_list",
            items_key="organisations",
            search_term=search_term,
            searchable=True,
            search_placeholder="Name or ID",
            edit_url_name="indigo_admin_organisation_edit",
            add_url_name="indigo_admin_organisation_new",
            add_label="Organisation",
            menu_groups=[
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
            ],
            search_extra_template="indigo/admin/includes/organisation_goto.html",
        ),
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


@permission_admin_or_data_steward_required()
def admin_organisation_index(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return _admin_record_page(
        request,
        organisation,
        record_title="Organisation",
        type_public_id=TYPE_ORGANISATION_PUBLIC_ID,
        url_prefix="organisation",
        list_title="Organisations",
        extra_actions=[
            ("Projects Using This", "indigo_admin_organisation_projects", True),
            ("Pipelines Using This", "indigo_admin_organisation_pipelines", True),
        ],
        spreadsheets=[
            ("Download Form", "indigo_admin_organisation_download_form"),
            ("Upload/Import Form", "indigo_admin_organisation_import_form"),
        ],
        notes=[DOWNLOAD_FORM_NOTE],
    )


@permission_required("indigo.admin")
def admin_organisation_projects(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return _related_records_page(
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
    return _related_records_page(
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


@permission_admin_or_data_steward_required()
def admin_organisation_download_form(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    data = convert_organisation_data_to_spreadsheetforms_data(
        organisation, public_only=False
    )

    spreadsheetforms.api.put_data_in_form(
        settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
            "spreadsheet_form_guide"
        ],
        data,
        out_file,
    )

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=organisation.xlsx"

    return response


@permission_admin_or_data_steward_required()
def admin_organisation_import_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        data = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = OrganisationImportForm(request.POST, request.FILES)

        # Check if the form is valid:
        if form.is_valid():

            # get data
            version = indigo.utils.get_organisation_spreadsheet_version(
                request.FILES["file"].temporary_file_path()
            )
            if (
                version
                not in settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
                    "spreadsheet_form_guide_spec_versions"
                ].keys()
            ):
                raise Exception("This seems to not be a organisation spreadsheet?")

            import_json = spreadsheetforms.api.get_data_from_form_with_guide_spec(
                settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
                    "spreadsheet_form_guide_spec_versions"
                ][version],
                request.FILES["file"].temporary_file_path(),
                date_format=getattr(
                    settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
                ),
                missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
            )

            # process the data in form.cleaned_data as required
            # Save the event
            new_event_datas = extract_edits_from_organisation_spreadsheet(
                data, import_json
            )
            newEvent(
                new_event_datas,
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            messages.add_message(
                request,
                messages.INFO,
                "The data has been imported; remember to moderate it!",
            )
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_index",
                    kwargs={"public_id": data.public_id},
                )
            )

        # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationImportForm()

    return render(
        request, "indigo/admin/import_form.html", _subpage_context(data, form=form)
    )


@permission_admin_or_data_steward_required()
@transaction.atomic
def admin_organisations_new(request):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")

    # If this is a POST request then process the Form data
    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = OrganisationNewForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = indigo.utils.get_next_record_id(type)
            data = NewEventData(
                type,
                id,
                {"name": {"value": form.cleaned_data["name"]}},
                approved=True,
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            messages.add_message(
                request,
                messages.INFO,
                "Created. Now fill in the rest of the details; they will be available once they have been moderated.",
            )

            # redirect to the edit form
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_edit",
                    kwargs={"public_id": id},
                )
            )

    # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationNewForm()

    return _new_page(request, TYPE_ORGANISATION_PUBLIC_ID, form)


@permission_admin_or_data_steward_required()
def admin_organisation_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    edits = Edit.objects.filter(record=record, approval_event=None, refusal_event=None)

    if request.method == "POST" and request.user.has_perm("indigo.admin"):

        # TODO check CSFR

        actions = []
        for edit in edits:
            action = request.POST.get("action_" + str(edit.id))
            if action == "approve":
                actions.append(jsondataferret.pythonapi.newevent.NewEventApproval(edit))
            elif action == "reject":
                actions.append(
                    jsondataferret.pythonapi.newevent.NewEventRejection(edit)
                )

        if actions:
            jsondataferret.pythonapi.newevent.newEvent(
                actions, user=request.user, comment=request.POST.get("comment")
            )
            _add_moderation_message(request, actions)

        return HttpResponseRedirect(
            reverse(
                "indigo_admin_organisation_index",
                kwargs={"public_id": public_id},
            )
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.changes = _edit_changes(edit, record)

    return render(
        request,
        "indigo/admin/moderate.html",
        _subpage_context(record, edits=edits),
    )


@permission_admin_or_data_steward_required()
def admin_organisation_history(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    return _record_history_page(request, record)


########################### Admin - funds & assessment resources


class AdminModelDownloadBlankForm(PermissionRequiredMixin, View, ABC):
    def get(self, request):
        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )

        spreadsheetforms.api.make_empty_form(self._guide_file_name, out_file)

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response


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


class AdminFundDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

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


class AdminModelList(PermissionRequiredMixin, View, ABC):
    """A list of records of one type. Each list says (in its class variables):

    _list_title / _noun_plural / _add_label: the words to use
    _url_prefix: the start of its view names, eg "fund" for indigo_admin_fund_index
    _search_keys: the keys of the data whose value can be searched, as well as the ID
    _menu_groups: what goes in the More menu (see indigo.listpages.visible_menu)"""

    _search_keys = []
    _menu_groups = []

    def get(self, request):
        cls = self.__class__
        try:
            type = Type.objects.get(public_id=cls._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        datas = Record.objects.filter(type=type).order_by("public_id")
        search_term = request.GET.get("search", "").strip()
        if search_term and cls._search_keys:
            datas = datas.filter(
                search_filter(search_term, "cached_data", cls._search_keys)
            )
        return render(
            request,
            "indigo/admin/list.html",
            list_context(
                request,
                datas,
                title=cls._list_title,
                noun_plural=cls._noun_plural,
                name_field="cached_data",
                index_url_name=f"indigo_admin_{cls._url_prefix}_index",
                list_url_name=f"indigo_admin_{cls._url_prefix}_list",
                items_key="datas",
                search_term=search_term,
                searchable=bool(cls._search_keys),
                search_placeholder=f"{cls._add_label} ID or name",
                edit_url_name=f"indigo_admin_{cls._url_prefix}_edit",
                add_url_name=f"indigo_admin_{cls._url_prefix}_new",
                add_label=cls._add_label,
                menu_groups=cls._menu_groups,
            ),
        )


def _blank_form_menu(url_name):
    return [
        {
            "heading": "Spreadsheets",
            "items": [{"label": "Download Blank Form", "url_name": url_name}],
        }
    ]


class AdminFundList(AdminModelList):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Funds"
    _noun_plural = "funds"
    _add_label = "Fund"
    _url_prefix = "fund"
    _menu_groups = _blank_form_menu("indigo_admin_fund_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceList(AdminModelList):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Assessment Resources"
    _noun_plural = "assessment resources"
    _add_label = "Assessment Resource"
    _url_prefix = "assessment_resource"
    _menu_groups = _blank_form_menu(
        "indigo_admin_assessment_resource_download_blank_form"
    )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineList(AdminModelList):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _search_keys = ["name", "alternative_names"]
    _list_title = "Pipelines"
    _noun_plural = "pipelines"
    _add_label = "Pipeline"
    _url_prefix = "pipeline"
    _menu_groups = _blank_form_menu("indigo_admin_pipeline_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeList(AdminModelList):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Joining Up Initiatives"
    _noun_plural = "Joining Up Initiatives"
    _add_label = "Joining Up Initiative"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelIndex(PermissionRequiredMixin, View, ABC):
    """The admin page of one record of a type. Each says (in its class variables):

    _record_title / _list_title / _url_prefix: the words to use, and the start of its view names
    _extra_actions: (label, url name, admin only?) for pages this type has of its own
    _spreadsheets / _notes: what goes in the Spreadsheets part of the More menu, if there is one"""

    _extra_actions = ()
    _spreadsheets = ()
    _notes = ()

    def get(self, request, public_id):
        cls = self.__class__
        try:
            data = cls._model.objects.get(public_id=public_id)
        except cls._model.DoesNotExist:
            raise Http404("Data does not exist")
        return _admin_record_page(
            request,
            data,
            record_title=cls._record_title,
            type_public_id=cls._model.type_id,
            url_prefix=cls._url_prefix,
            list_title=cls._list_title,
            extra_actions=cls._extra_actions,
            spreadsheets=cls._spreadsheets,
            notes=cls._notes,
        )


def _form_downloads(prefix):
    return [
        ("Download Form", f"indigo_admin_{prefix}_download_form"),
        ("Upload/Import Form", f"indigo_admin_{prefix}_import_form"),
    ]


class AdminFundIndex(AdminModelIndex):
    _model = Fund
    _record_title = "Fund"
    _list_title = "Funds"
    _url_prefix = "fund"
    _extra_actions = [("Projects Using This", "indigo_admin_fund_projects", True)]
    _spreadsheets = _form_downloads("fund")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceIndex(AdminModelIndex):
    _model = AssessmentResource
    _record_title = "Assessment Resource"
    _list_title = "Assessment Resources"
    _url_prefix = "assessment_resource"
    _spreadsheets = _form_downloads("assessment_resource")

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
    _spreadsheets = _form_downloads("pipeline")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeIndex(AdminModelIndex):
    _model = JoiningUpInitiative
    _record_title = "Joining Up Initiative"
    _list_title = "Joining Up Initiatives"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


@permission_required("indigo.admin")
def admin_fund_projects(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    return _related_records_page(
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


class AdminModelDownloadForm(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )

        data_for_form = self._get_data_for_form(data)

        spreadsheetforms.api.put_data_in_form(
            self.__class__._guide_file_name, data_for_form, out_file
        )

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response

    def has_permission_with_data(self, data):
        return True


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


class AdminModelImportForm(PermissionRequiredMixin, View, ABC):
    """Provides a 1 stage import process.

    This is only suitable for small spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        return render(
            request,
            "indigo/admin/import_form.html",
            _subpage_context(data.record, form=self.__class__._form_class()),
        )

    def post(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        form = self.__class__._form_class(request.POST, request.FILES)
        if form.is_valid():
            # get data
            import_json = spreadsheetforms.api.get_data_from_form_with_guide_spec(
                settings.JSONDATAFERRET_TYPE_INFORMATION[self.__class__._model.type_id][
                    "spreadsheet_form_guide_spec"
                ],
                request.FILES["file"].temporary_file_path(),
                date_format=getattr(
                    settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
                ),
                missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
            )

            # process the data in form.cleaned_data as required
            # Save the event
            newEvent(
                self._get_edits(data, import_json),
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            messages.add_message(
                request,
                messages.INFO,
                "The data has been imported; remember to moderate it!",
            )
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": data.public_id},
                )
            )
        else:
            return render(
                request,
                "indigo/admin/import_form.html",
                _subpage_context(data.record, form=form),
            )


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


class AdminModelImportFormStage1Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 1 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        form = ModelImportStage1Of2Form()

        return render(
            request,
            "indigo/admin/import_form.html",
            _subpage_context(record, form=form),
        )

    def post(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        form = ModelImportStage1Of2Form(request.POST, request.FILES)

        if form.is_valid():

            # Save the data
            import_data = self._import_model()
            import_data.user = request.user
            self._set_record_on_import_model(record, import_data)
            with open(request.FILES["file"].temporary_file_path(), "rb") as fp:
                import_data.file_data = fp.read()
            import_data.save()

            # Make celery call to start background worker
            self._send_message_to_worker(import_data)

            # redirect to a new URL so user can wait for stage 2 of the process to be ready
            return HttpResponseRedirect(
                reverse(
                    self._redirect_view,
                    kwargs={
                        "public_id": record.public_id,
                        "import_id": import_data.id,
                    },
                )
            )

        else:

            return render(
                request,
                "indigo/admin/import_form.html",
                _subpage_context(record, form=form),
            )

    def has_permission_with_data(self, data):
        return True


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


class AdminModelImportFormStage2Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 2 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def _setup(self, request, public_id, import_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record
        type = record.type

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        try:
            import_data = self._import_model.objects.get(id=import_id)
        except self._import_model.DoesNotExist:
            raise Http404("Import does not exist")

        if not self._check_record_and_import_are_linked(record, import_data):
            raise Http404("Import is for another data item")
        if import_data.user != request.user:
            raise Http404("Import is for another user")
        if import_data.imported:
            raise Http404("Import already done")

        if import_data.exception:
            return (
                render(
                    request,
                    "indigo/admin/import_message.html",
                    _subpage_context(
                        record,
                        message="There was a problem. Please contact support.",
                    ),
                ),
                None,
                None,
                None,
            )

        if import_data.file_not_valid:
            return (
                render(
                    request,
                    "indigo/admin/import_message.html",
                    _subpage_context(
                        record,
                        message="That does not seem to be a "
                        + record.type.public_id
                        + " spreadsheet, so it can not be imported.",
                    ),
                ),
                None,
                None,
                None,
            )

        if not import_data.data:
            return (
                render(
                    request,
                    "indigo/admin/import_message.html",
                    _subpage_context(
                        record,
                        message="We are processing your file, please wait ...",
                        refresh_url=reverse(
                            f"indigo_admin_{record.type.public_id}_import_form_stage_2",
                            kwargs={
                                "public_id": record.public_id,
                                "import_id": import_data.id,
                            },
                        ),
                    ),
                ),
                None,
                None,
                None,
            )

        return None, type, record, import_data

    def get(self, request, public_id, import_id):

        view, type, record, import_data = self._setup(request, public_id, import_id)
        if view:
            return view

        # Because a spreadsheet with deleted tabs may have been uploaded,
        # import_data.data isn't the complete data for this record.
        # So merge import data on top of current data and use that to make a data quality report.
        new_event_datas = [
            d
            for d in self._get_edits(record, import_data.data)
            if d.record.type.public_id == self._type_public_id
        ]
        data_quality_report = self._dqr_class(
            new_event_datas[
                0
            ].get_new_data_when_event_applied_to_latest_record_cached_data()
        )
        level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

        form = ModelImportStage2Of2Form()

        return render(
            request,
            "indigo/admin/import_stage_2.html",
            _subpage_context(record, form=form, level_zero_errors=level_zero_errors),
        )

    def post(self, request, public_id, import_id):

        view, type, record, import_data = self._setup(request, public_id, import_id)
        if view:
            return view

        form = ModelImportStage2Of2Form(request.POST, request.FILES)

        if form.is_valid():

            # Save the event
            new_event_datas = self._get_edits(record, import_data.data)
            newEvent(
                new_event_datas,
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # mark import done
            import_data.imported = Now()
            import_data.save()

            # redirect to project page with message
            messages.add_message(
                request,
                messages.INFO,
                "The data has been imported; remember to moderate it!",
            )
            return HttpResponseRedirect(
                reverse(
                    self._redirect_view,
                    kwargs={"public_id": record.public_id},
                )
            )

        else:
            data_quality_report = self._dqr_class(import_data.data)
            level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

            return render(
                request,
                "indigo/admin/import_stage_2.html",
                _subpage_context(
                    record, form=form, level_zero_errors=level_zero_errors
                ),
            )

    def has_permission_with_data(self, data):
        return True


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


class AdminModelChangeStatus(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        record = data.record

        form = RecordChangeStatusForm()

        return render(
            request,
            "indigo/admin/change_status.html",
            _subpage_context(record, form=form),
        )

    def post(self, request, public_id):

        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        record = data.record

        # Create a form instance and populate it with data from the request (binding):
        form = RecordChangeStatusForm(request.POST)

        # For some users, not all combinations of actions are valid.
        if not request.user.has_perm("indigo.admin"):
            if form.data["status"] == "PUBLIC" and form.data["when"] == "immediate":
                form.add_error(
                    None,
                    ValidationError(
                        "With this access level, you can not make something public without submitting if for moderation."
                    ),
                )

        # Check if the form is valid:
        if form.is_valid():
            approved = form.cleaned_data["when"] == "immediate"

            # Save the event
            new_event_data = NewEventData(
                record.type,
                record,
                {"status": form.cleaned_data["status"]},
                mode=jsondataferret.EVENT_MODE_MERGE,
                approved=approved,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            messages.add_message(
                request,
                messages.INFO,
                "Change made!" if approved else "Change sent for moderation.",
            )
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": record.public_id},
                )
            )

        return render(
            request,
            "indigo/admin/change_status.html",
            _subpage_context(record, form=form),
        )

    def has_permission_with_data(self, data):
        return True


class AdminProjectChangeStatus(AdminModelChangeStatus):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminOrganisationChangeStatus(AdminModelChangeStatus):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _redirect_view = "indigo_admin_organisation_index"

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


class AdminPipelineChangeStatus(AdminModelChangeStatus):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"

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


class AdminJoiningUpInitiativeChangeStatus(AdminModelChangeStatus):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelNew(PermissionRequiredMixin, View, ABC):
    def get(self, request):
        form = self.__class__._form_class()
        return _new_page(request, self.__class__._type_public_id, form)

    @method_decorator(transaction.atomic)
    def post(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        form = self.__class__._form_class(request.POST)
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = indigo.utils.get_next_record_id(type)
            data = NewEventData(
                type,
                id,
                {"name": {"value": form.cleaned_data["name"]}},
                approved=True,
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            messages.add_message(
                request,
                messages.INFO,
                "Created. Now fill in the rest of the details; they will be available once they have been moderated.",
            )

            # redirect to the edit form
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": id},
                )
            )

        return _new_page(request, self.__class__._type_public_id, form)


class AdminFundNew(AdminModelNew):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = FundNewForm
    _redirect_view = "indigo_admin_fund_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceNew(AdminModelNew):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = AssessmentResourceNewForm
    _redirect_view = "indigo_admin_assessment_resource_edit"

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


class AdminModelJSONFormNew(PermissionRequiredMixin, View, ABC):
    def _page(self, request, form):
        return _new_page(request, self.__class__._type_public_id, form, full_form=True)

    def get(self, request):
        return self._page(request, self.__class__._form_class())

    @method_decorator(transaction.atomic)
    def post(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        form = self.__class__._form_class(request.POST)
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = indigo.utils.get_next_record_id(type)

            data = NewEventData(
                type,
                id,
                form.cleaned_data["data"],
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            # redirect to page with message
            messages.add_message(
                request,
                messages.INFO,
                "New record submitted. The data will not be available until it's been moderated.",
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": id},
                )
            )

        return self._page(request, form)


class AdminJoiningUpInitiativeNew(AdminModelJSONFormNew):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeNewForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelEdit(PermissionRequiredMixin, View, ABC):
    """The page for editing a record. Each says (in its class variables) _record_title and _list_title, and
    _redirect_view, the record's own page, which also names the rest of its views."""

    def get_template(self):
        return "indigo/admin/edit.html"

    def _context(self, form, instance):
        cls = self.__class__
        name = (instance.data_private or {}).get("name")
        return {
            "form": form,
            "instance": instance,
            "record_title": cls._record_title,
            "list_title": cls._list_title,
            "list_url": reverse(cls._redirect_view.removesuffix("_index") + "_list"),
            "record_url": reverse(
                cls._redirect_view, kwargs={"public_id": instance.public_id}
            ),
            "display_name": name.get("value", "") if isinstance(name, dict) else "",
        }

    def has_permission_with_data(self, data):
        return True

    def _get_edits(self, record, data):
        return extract_edits_from_form(self._type_public_id, record, data)

    def get(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            instance = Model.objects.get(public_id=public_id)
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")
        if not self.has_permission_with_data(instance):
            raise PermissionDenied("You can not see data")

        form = Form(initial={"data": instance.data_private})
        return render(request, self.get_template(), self._context(form, instance))

    @method_decorator(transaction.atomic)
    def post(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
            instance = Model.objects.get(public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")
        if not self.has_permission_with_data(instance):
            raise PermissionDenied("You can not see data")

        form = Form(request.POST, request.FILES)

        if form.is_valid():
            data = form.cleaned_data["data"]

            new_event_datas = self._get_edits(record, data)

            newEvent(
                new_event_datas, user=request.user, comment=form.cleaned_data["comment"]
            )

            # redirect to page with message
            messages.add_message(
                request,
                messages.INFO,
                "Updates submitted. The changes will not be available until the updates have been moderated.",
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": public_id},
                )
            )

        return render(request, self.get_template(), self._context(form, instance))


class AdminJoiningUpInitiativeEdit(AdminModelEdit):
    _model = JoiningUpInitiative
    _record_title = "Joining Up Initiative"
    _list_title = "Joining Up Initiatives"
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeEditForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


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


class AdminModelModerate(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        return self.post(request, public_id)

    def post(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._model.type_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        edits = Edit.objects.filter(
            record=record, approval_event=None, refusal_event=None
        )

        if request.method == "POST" and request.user.has_perm("indigo.admin"):

            # TODO check CSFR

            actions = []
            for edit in edits:
                action = request.POST.get("action_" + str(edit.id))
                if action == "approve":
                    actions.append(
                        jsondataferret.pythonapi.newevent.NewEventApproval(edit)
                    )
                elif action == "reject":
                    actions.append(
                        jsondataferret.pythonapi.newevent.NewEventRejection(edit)
                    )

            if actions:
                jsondataferret.pythonapi.newevent.newEvent(
                    actions, user=request.user, comment=request.POST.get("comment")
                )
                _add_moderation_message(request, actions)
                return HttpResponseRedirect(
                    reverse(
                        self.__class__._redirect_view,
                        kwargs={"public_id": record.public_id},
                    )
                )

        for edit in edits:
            edit.changes = _edit_changes(edit, record)

        return render(
            request,
            "indigo/admin/moderate.html",
            _subpage_context(record, edits=edits),
        )


class AdminFundModerate(AdminModelModerate):
    _model = Fund
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceModerate(AdminModelModerate):
    _model = AssessmentResource
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineModerate(AdminModelModerate):
    _model = Pipeline
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeModerate(AdminModelModerate):
    _model = JoiningUpInitiative
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelHistory(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        return _record_history_page(request, record)


class AdminFundHistory(AdminModelHistory):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceHistory(AdminModelHistory):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineHistory(AdminModelHistory):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeHistory(AdminModelHistory):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelDataQualityReport(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        dqr = self.__class__._data_quality_report(record.cached_data)

        return render(
            request,
            "indigo/admin/data_quality_report.html",
            _subpage_context(
                record,
                errors_by_priority_level=dqr.get_errors_in_priority_levels(),
                data_quality_report=dqr,
            ),
        )

    def has_permission_with_data(self, data):
        return True


class AdminProjectDataQualityReport(AdminModelDataQualityReport):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _data_quality_report = DataQualityReportForProject

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminPipelineDataQualityReport(AdminModelDataQualityReport):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _data_quality_report = DataQualityReportForPipeline

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


########################### Admin - sandboxes


@permission_admin_or_data_steward_required()
def admin_sandbox_list(request):
    sandboxes = Sandbox.objects.all()
    return render(
        request,
        "indigo/admin/sandboxes.html",
        {"sandboxes": sandboxes},
    )


@permission_admin_or_data_steward_required()
def admin_sandbox_index(request, public_id):
    try:
        sandbox = Sandbox.objects.get(public_id=public_id)
    except Sandbox.DoesNotExist:
        raise Http404("Sandbox does not exist")
    return render(
        request,
        "indigo/admin/sandbox/index.html",
        {"sandbox": sandbox},
    )


########################### Admin - Event


@permission_admin_or_data_steward_required()
def admin_event_index(request, event_id):
    try:
        event = Event.objects.get(public_id=event_id)
    except Event.DoesNotExist:
        raise Http404("Event does not exist")
    if not user_can_access_event(request.user, event):
        raise PermissionDenied("You can not see data")
    edits_created = [
        e for e in event.edits_created.all() if user_can_access_edit(request.user, e)
    ]
    edits_approved = [
        e for e in event.edits_approved.all() if user_can_access_edit(request.user, e)
    ]
    edits_refused = [
        e for e in event.edits_refused.all() if user_can_access_edit(request.user, e)
    ]
    edits_only_created = [edit for edit in edits_created if edit not in edits_approved]
    if edits_approved:
        records_with_changes = [
            {"record": r} for r in event.get_records(approved_edits_only=True)
        ]
        for record_with_changes in records_with_changes:
            try:
                record_with_changes[
                    "cached_record_history"
                ] = CachedRecordHistory.objects.get(
                    record=record_with_changes["record"], event=event
                )
                record_with_changes["last_cached_record_history"] = record_with_changes[
                    "cached_record_history"
                ].get_previous_cached_record_history()
            except CachedRecordHistory.DoesNotExist:
                pass
    else:
        records_with_changes = []
    return render(
        request,
        "indigo/admin/event/index.html",
        {
            "event": event,
            "edits_created": edits_created,
            "edits_approved": edits_approved,
            "edits_refused": edits_refused,
            "edits_only_created": edits_only_created,
            "records_with_changes": records_with_changes,
        },
    )


@permission_admin_or_data_steward_required()
def admin_edit_index(request, edit_id):
    try:
        edit = Edit.objects.get(public_id=edit_id)
    except Edit.DoesNotExist:
        raise Http404("Edit does not exist")
    if not user_can_access_edit(request.user, edit):
        raise PermissionDenied("You can not see data")
    return render(
        request,
        "indigo/admin/edit/index.html",
        {
            "edit": edit,
        },
    )


########################### Admin - Moderate


# What the To Moderate page shows: each type, its title, and the start of its view names
MODERATION_TYPES = [
    (TYPE_PROJECT_PUBLIC_ID, "Projects", "project"),
    (TYPE_ORGANISATION_PUBLIC_ID, "Organisations", "organisation"),
    (TYPE_FUND_PUBLIC_ID, "Funds", "fund"),
    (TYPE_PIPELINE_PUBLIC_ID, "Pipelines", "pipeline"),
    (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "Assessment Resources", "assessment_resource"),
    (
        TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
        "Joining Up Initiatives",
        "joining_up_initiative",
    ),
]


def _records_waiting_for_moderation(type_public_id):
    """The records of this type with edits waiting to be moderated, oldest waiting first.

    Each is a dict of the record, its name, how many edits are waiting, since when, and who made the latest."""
    try:
        type = Type.objects.get(public_id=type_public_id)
    except Type.DoesNotExist:
        return []
    records = list(Record.objects.filter_needs_moderation_by_type(type))
    edits_by_record = {}
    for edit in (
        Edit.objects.filter(record__in=records, approval_event=None, refusal_event=None)
        .select_related("creation_event", "creation_event__user")
        .order_by("creation_event__created", "id")
    ):
        edits_by_record.setdefault(edit.record_id, []).append(edit)
    rows = []
    for record in records:
        edits = edits_by_record.get(record.id)
        if not edits:
            continue
        data = record.cached_data if isinstance(record.cached_data, dict) else {}
        name = data.get("name")
        rows.append(
            {
                "record": record,
                "name": name.get("value", "") if isinstance(name, dict) else "",
                "edit_count": len(edits),
                "waiting_since": edits[0].creation_event.created,
                "latest_user": edits[-1].creation_event.user,
            }
        )
    rows.sort(key=lambda row: row["waiting_since"])
    return rows


@permission_required("indigo.admin")
def admin_to_moderate(request):
    sections = [
        {
            "title": title,
            "anchor": prefix,
            "rows": _records_waiting_for_moderation(type_public_id),
            "index_url": f"indigo_admin_{prefix}_index",
            "moderate_url": f"indigo_admin_{prefix}_moderate",
        }
        for type_public_id, title, prefix in MODERATION_TYPES
    ]
    return render(
        request,
        "indigo/admin/to_moderate.html",
        {
            "sections": sections,
            "total": sum(len(section["rows"]) for section in sections),
            "empty_titles": [s["title"] for s in sections if not s["rows"]],
        },
    )
