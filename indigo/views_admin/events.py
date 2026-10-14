"""The site-wide History page, and the pages for one event or edit."""
import datetime
import urllib.parse

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from jsondataferret.models import CachedRecordHistory, Edit, Event

from indigo.filters import HistoryFilter
from indigo.listpages import paginate
from indigo.views_admin.common import (
    permission_admin_or_data_steward_required,
    user_can_access_edit,
    user_can_access_event,
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
