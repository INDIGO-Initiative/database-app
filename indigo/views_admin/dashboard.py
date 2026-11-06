"""The admin home page."""
from django.shortcuts import render

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    Project,
    Sandbox,
)
from indigo.views_admin.common import permission_admin_or_data_steward_required
from indigo.views_admin.to_moderate import count_records_needing_moderation


@permission_admin_or_data_steward_required()
def admin_index(request):
    user = request.user
    is_admin = user.has_perm("indigo.admin")

    # The "To Moderate" page is for admins, so only admins are told what is waiting
    def waiting(type_public_id):
        return count_records_needing_moderation(type_public_id) if is_admin else None

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
