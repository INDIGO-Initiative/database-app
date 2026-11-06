"""Helpers shared by the admin views: titles, the context of pages about a record, permissions and moderation messages."""
from abc import ABC

import jsondataferret
import jsondataferret.utils
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from jsondataferret.models import Edit, Event

import indigo.utils
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.listpages import paginate, visible_menu
from indigo.models import AdminUserHasPermissionsForProject, Project
from indigo.recordpages import build_record_sections

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


def new_page(request, type_public_id, form, full_form=False):
    """The page for adding a record: just a name to start with, or (full_form) the whole record in one go."""
    context = _list_context_for_type(type_public_id)
    context.update({"form": form, "full_form": full_form})
    return render(request, "indigo/admin/new.html", context)


def subpage_context(record, **extra):
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


def related_records_page(
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
        subpage_context(
            model_instance.record,
            related_title=related_title,
            related_noun=related_noun,
            links=links,
        ),
    )


def record_history_page(request, record):
    page_obj, pagination_get_params = paginate(
        request, _events_for_record_newest_first(record)
    )
    return render(
        request,
        "indigo/admin/record_history.html",
        subpage_context(
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


def edit_changes(edit, record):
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


def add_moderation_message(request, actions):
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


def admin_record_page(
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


class AdminModelRecordView(PermissionRequiredMixin, View, ABC):
    """The base of the views of one record. A type can add to who may see a record by overriding _check_access."""

    def _check_access(self, public_id):
        """Raise PermissionDenied if this user may not see the record with this public id. By default anyone with
        permission to use the view can."""


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


class ProjectAccessMixin:
    """For the views of one project: a data steward can only see the projects they have been given access to."""

    def _check_access(self, public_id):
        try:
            project = Project.objects.get(public_id=public_id)
        except Project.DoesNotExist:
            raise Http404("Record does not exist")
        if not user_can_access_project(self.request.user, project):
            raise PermissionDenied("You can not see project")


def add_schema_warnings_message(request, form):
    """If the data was saved although parts of it do not match the data standard, say so (see indigo/schemacheck.py)."""
    warnings = form.schema_warnings
    if not warnings:
        return
    shown = "; ".join(
        f"{problem.path or '(whole record)'}: {problem.message}"
        for problem in warnings[:5]
    )
    more = f" (and {len(warnings) - 5} more)" if len(warnings) > 5 else ""
    messages.add_message(
        request,
        messages.WARNING,
        f"Saved, but {len(warnings)} value{'s do' if len(warnings) != 1 else ' does'} not match the data standard: "
        f"{shown}{more}. The data quality report lists these.",
    )
