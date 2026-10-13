"""The To Moderate page, listing the records with edits waiting."""
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render
from jsondataferret.models import Edit, Record, Type

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)


def _count_records_needing_moderation(type_public_id):
    try:
        type = Type.objects.get(public_id=type_public_id)
    except Type.DoesNotExist:
        return 0
    return len(list(Record.objects.filter_needs_moderation_by_type(type)))


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
