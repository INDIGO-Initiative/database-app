"""The admin pages for sandboxes."""
from django.http import Http404
from django.shortcuts import render

from indigo.models import Sandbox
from indigo.views_admin.common import permission_admin_or_data_steward_required


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
