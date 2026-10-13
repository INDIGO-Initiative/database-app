"""Admin views for projects that have no class-based equivalent."""
import jsondataferret
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from jsondataferret.models import Edit, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.utils
from indigo import TYPE_PROJECT_PUBLIC_ID
from indigo.forms import ProjectNewForm
from indigo.listpages import list_context
from indigo.models import AdminUserHasPermissionsForProject, Project
from indigo.views_admin.common import (
    DOWNLOAD_FORM_NOTE,
    _add_moderation_message,
    _admin_record_page,
    _edit_changes,
    _new_page,
    _record_history_page,
    _subpage_context,
    permission_admin_or_data_steward_required,
    user_can_access_project,
)


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
