import csv
import os
import random
import tempfile

import jsondataferret
import jsondataferret.utils
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.db.models.functions import Now
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from jsondataferret.models import Edit, Event, Record, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.processdata
from indigo import (
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)

from .forms import (
    FundImportForm,
    FundNewForm,
    OrganisationImportForm,
    OrganisationNewForm,
    ProjectImportForm,
    ProjectImportStage2Form,
    ProjectMakeDisputedForm,
    ProjectMakePrivateForm,
    ProjectNewForm,
)
from .models import Fund, Organisation, Project, ProjectImport

########################### Home Page


def index(request):
    return render(request, "indigo/index.html")


########################### Public - Project


def projects_list(request):
    projects = Project.objects.filter(exists=True, status_public=True)
    return render(request, "indigo/projects.html", {"projects": projects},)


def projects_list_download(request):
    projects = Project.objects.filter(exists=True, status_public=True)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="projects.csv"'

    writer = csv.writer(response)
    writer.writerow(
        ["ID", "Project Name", "Fund Name", "Launch Date",]
    )
    for project in projects:
        row = [project.public_id]
        for key in ["/project_name", "/fund_name", "/launch_date"]:
            try:
                row.append(
                    jsonpointer.resolve_pointer(project.data_public, key + "/value")
                )
            except jsonpointer.JsonPointerException:
                row.append("")
        writer.writerow(row)

    return response


def project_index(request, public_id):
    try:
        project = Project.objects.get(
            exists=True, status_public=True, public_id=public_id
        )
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    if not project.status_public or not project.exists:
        raise Http404("Project does not exist")
    field_data = jsondataferret.utils.get_field_list_from_json(
        TYPE_PROJECT_PUBLIC_ID, project.data_public
    )
    return render(
        request,
        "indigo/project/index.html",
        {"project": project, "field_data": field_data},
    )


def project_download_form(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    if not project.status_public or not project.exists:
        raise Http404("Project does not exist")

    data = indigo.processdata.add_other_records_to_project(
        project.public_id, project.data_public, public_only=True
    )
    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "project-public.xlsx",
    )
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = (
            "inline; filename=project" + project.public_id + ".xlsx"
        )
    return response


########################### Public - Project - API


def api1_projects_list(request):
    projects = Project.objects.filter()
    data = {
        "projects": [
            {"id": p.public_id, "public": (p.exists and p.status_public)}
            for p in projects
        ]
    }
    return JsonResponse(data)


def api1_project_index(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    if not project.status_public or not project.exists:
        raise Http404("Project does not exist")

    data = {"project": {"id": project.public_id, "data": project.data_public,}}
    return JsonResponse(data)


########################### Admin


@permission_required("indigo.admin")
def admin_index(request):
    return render(request, "indigo/admin/index.html")


########################### Admin - Projects


@permission_required("indigo.admin")
def admin_project_download_blank_form(request):
    type_data = settings.JSONDATAFERRET_TYPE_INFORMATION.get(TYPE_PROJECT_PUBLIC_ID, {})
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
        response["Content-Disposition"] = "inline; filename=project.xlsx"

    return response


@permission_required("indigo.admin")
def admin_projects_list(request):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    projects = Record.objects.filter(type=type)
    return render(request, "indigo/admin/projects.html", {"projects": projects},)


@permission_required("indigo.admin")
def admin_project_index(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    field_data = jsondataferret.utils.get_field_list_from_json(
        TYPE_PROJECT_PUBLIC_ID, project.data_private
    )
    return render(
        request,
        "indigo/admin/project/index.html",
        {"project": project, "field_data": field_data},
    )


@permission_required("indigo.admin")
def admin_project_download_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    data = indigo.processdata.add_other_records_to_project(
        record.public_id, record.cached_data, public_only=False
    )
    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "project.xlsx",
    )
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=project.xlsx"
    return response


@permission_required("indigo.admin")
def admin_project_import_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
        project = Project.objects.get(public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")
    except Project.DoesNotExist:
        raise Http404("Project does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectImportForm(request.POST, request.FILES)

        # Check if the form is valid:
        if form.is_valid():

            # get data
            guide_file = os.path.join(
                settings.BASE_DIR, "indigo", "spreadsheetform_guides", "project.xlsx",
            )
            json_data = spreadsheetforms.api.get_data_from_form(
                guide_file,
                request.FILES["file"].temporary_file_path(),
                date_format=getattr(
                    settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
                ),
            )

            # Save the data
            project_import = ProjectImport()
            project_import.user = request.user
            project_import.project = project
            project_import.data = json_data
            project_import.save()

            # redirect to a new URL for stage 2 of the process
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_import_form_stage_2",
                    kwargs={
                        "public_id": project.public_id,
                        "import_id": project_import.id,
                    },
                )
            )

        # If this is a GET (or any other method) create the default form.
    else:
        form = ProjectImportForm()

    context = {
        "record": record,
        "project": project,
        "form": form,
    }

    return render(request, "indigo/admin/project/import_form.html", context)


@permission_required("indigo.admin")
def admin_project_import_form_stage_2(request, public_id, import_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
        project = Project.objects.get(public_id=public_id)
        project_import = ProjectImport.objects.get(id=import_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    except ProjectImport.DoesNotExist:
        raise Http404("Import does not exist")

    if project_import.project != project:
        raise Http404("Import is for another project")
    if project_import.user != request.user:
        raise Http404("Import is for another user")
    if project_import.imported:
        raise Http404("Import already done")

    (
        source_ids_used_that_are_not_in_sources_table,
        source_table_entries_that_are_not_used,
    ) = indigo.processdata.check_project_data_for_source_errors(project_import.data)

    can_import_now = len(source_ids_used_that_are_not_in_sources_table) == 0

    if request.method == "POST" and can_import_now:

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectImportStage2Form(request.POST, request.FILES)

        # Check if the form is valid:
        if form.is_valid():

            # process the data as required
            # Save the event
            new_event_datas = indigo.processdata.extract_edits_from_project_import(
                record, project_import.data
            )
            newEvent(
                new_event_datas,
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # mark import done
            project_import.imported = Now()
            project_import.save()

            # redirect to a new URL for stage 2 of the process
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_index",
                    kwargs={"public_id": project.public_id},
                )
            )

        # If this is a GET (or any other method) create the default form.
    else:
        form = ProjectImportStage2Form()

    context = {
        "record": record,
        "project": project,
        "form": form,
        "source_ids_used_that_are_not_in_sources_table": source_ids_used_that_are_not_in_sources_table,
        "source_table_entries_that_are_not_used": source_table_entries_that_are_not_used,
        "can_import_now": can_import_now,
    }

    return render(request, "indigo/admin/project/import_form_stage_2.html", context)


@permission_required("indigo.admin")
def admin_project_make_private(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectMakePrivateForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():

            # Save the event
            new_event_data = NewEventData(
                type,
                record,
                {"status": "PRIVATE"},
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_index",
                    kwargs={"public_id": record.public_id},
                )
            )

    else:

        form = ProjectMakePrivateForm()

    context = {
        "record": record,
        "form": form,
    }

    return render(request, "indigo/admin/project/make_private.html", context,)


@permission_required("indigo.admin")
def admin_project_make_disputed(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectMakeDisputedForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():

            # Save the event
            new_event_data = NewEventData(
                type,
                record,
                {"status": "DISPUTED"},
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_index",
                    kwargs={"public_id": record.public_id},
                )
            )

    else:

        form = ProjectMakeDisputedForm()

    context = {
        "record": record,
        "form": form,
    }

    return render(request, "indigo/admin/project/make_disputed.html", context,)


@permission_required("indigo.admin")
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
            id = form.cleaned_data["id"]
            existing_record = Record.objects.filter(type=type, public_id=id)
            if existing_record:
                form.add_error("id", "This ID already exists")
            else:
                data = NewEventData(
                    type,
                    id,
                    {"name": {"value": form.cleaned_data["name"]}},
                    approved=True,
                )
                newEvent(
                    [data], user=request.user, comment=form.cleaned_data["comment"]
                )

                # redirect to a new URL:
                return HttpResponseRedirect(
                    reverse("indigo_admin_project_index", kwargs={"public_id": id},)
                )

    # If this is a GET (or any other method) create the default form.
    else:
        form = ProjectNewForm()

    context = {
        "form": form,
    }

    return render(request, "indigo/admin/project/new.html", context)


@permission_required("indigo.admin")
def admin_project_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    edits = Edit.objects.filter(record=record, approval_event=None, refusal_event=None)

    if request.method == "POST":

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

        return HttpResponseRedirect(
            reverse("indigo_admin_project_index", kwargs={"public_id": public_id},)
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.field_datas = jsondataferret.utils.get_field_list_from_json(
            TYPE_PROJECT_PUBLIC_ID, edit.data
        )

    return render(
        request,
        "indigo/admin/project/moderate.html",
        {"type": type, "record": record, "edits": edits},
    )


@permission_required("indigo.admin")
def admin_project_history(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    events = Event.objects.filter_by_record(record)

    return render(
        request,
        "indigo/admin/project/history.html",
        {"type": type, "record": record, "events": events},
    )


########################### Admin - Organisations


@permission_required("indigo.admin")
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


@permission_required("indigo.admin")
def admin_organisations_list(request):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    organisations = Record.objects.filter(type=type)
    return render(
        request, "indigo/admin/organisations.html", {"organisations": organisations},
    )


@permission_required("indigo.admin")
def admin_organisation_index(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    field_data = jsondataferret.utils.get_field_list_from_json(
        TYPE_ORGANISATION_PUBLIC_ID, organisation.data_private
    )
    return render(
        request,
        "indigo/admin/organisation/index.html",
        {"organisation": organisation, "field_data": field_data},
    )


@permission_required("indigo.admin")
def admin_organisation_download_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "organisation.xlsx",
    )

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    data = record.cached_data
    data["id"] = record.public_id

    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=organisation.xlsx"

    return response


@permission_required("indigo.admin")
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
            guide_file = os.path.join(
                settings.BASE_DIR,
                "indigo",
                "spreadsheetform_guides",
                "organisation.xlsx",
            )
            json_data = spreadsheetforms.api.get_data_from_form(
                guide_file,
                request.FILES["file"].temporary_file_path(),
                date_format=getattr(
                    settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
                ),
            )
            del json_data["id"]

            # process the data in form.cleaned_data as required
            # Save the event
            new_event_data = NewEventData(
                TYPE_ORGANISATION_PUBLIC_ID,
                data.public_id,
                json_data,
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_index",
                    kwargs={"public_id": data.public_id},
                )
            )

        # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationImportForm()

    context = {
        "record": data,
        "form": form,
    }

    return render(request, "indigo/admin/organisation/import_form.html", context)


@permission_required("indigo.admin")
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
            id = form.cleaned_data["id"]
            existing_record = Record.objects.filter(type=type, public_id=id)
            if existing_record:
                form.add_error("id", "This ID already exists")
            else:
                data = NewEventData(
                    type,
                    id,
                    {"name": {"value": form.cleaned_data["name"]}},
                    approved=True,
                )
                newEvent(
                    [data], user=request.user, comment=form.cleaned_data["comment"]
                )

                # redirect to a new URL:
                return HttpResponseRedirect(
                    reverse(
                        "indigo_admin_organisation_index", kwargs={"public_id": id},
                    )
                )

    # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationNewForm()

    context = {
        "form": form,
    }

    return render(request, "indigo/admin/organisation/new.html", context)


@permission_required("indigo.admin")
def admin_organisation_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    edits = Edit.objects.filter(record=record, approval_event=None, refusal_event=None)

    if request.method == "POST":

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

        return HttpResponseRedirect(
            reverse("indigo_admin_organisation_index", kwargs={"public_id": public_id},)
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.field_datas = jsondataferret.utils.get_field_list_from_json(
            TYPE_ORGANISATION_PUBLIC_ID, edit.data
        )

    return render(
        request,
        "indigo/admin/organisation/moderate.html",
        {"type": type, "record": record, "edits": edits},
    )


@permission_required("indigo.admin")
def admin_organisation_history(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    events = Event.objects.filter_by_record(record)

    return render(
        request,
        "indigo/admin/organisation/history.html",
        {"type": type, "record": record, "events": events},
    )


########################### Admin - funds


@permission_required("indigo.admin")
def admin_fund_download_blank_form(request):
    type_data = settings.JSONDATAFERRET_TYPE_INFORMATION.get(TYPE_FUND_PUBLIC_ID, {})
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
        response["Content-Disposition"] = "inline; filename=fund.xlsx"

    return response


@permission_required("indigo.admin")
def admin_funds_list(request):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    funds = Record.objects.filter(type=type)
    return render(request, "indigo/admin/funds.html", {"funds": funds},)


@permission_required("indigo.admin")
def admin_fund_index(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    field_data = jsondataferret.utils.get_field_list_from_json(
        TYPE_FUND_PUBLIC_ID, fund.data_private
    )
    return render(
        request,
        "indigo/admin/fund/index.html",
        {"fund": fund, "field_data": field_data},
    )


@permission_required("indigo.admin")
def admin_fund_download_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "fund.xlsx",
    )

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    data = record.cached_data
    data["id"] = record.public_id

    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=fund.xlsx"

    return response


@permission_required("indigo.admin")
def admin_fund_import_form(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        data = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = FundImportForm(request.POST, request.FILES)

        # Check if the form is valid:
        if form.is_valid():

            # get data
            guide_file = os.path.join(
                settings.BASE_DIR, "indigo", "spreadsheetform_guides", "fund.xlsx",
            )
            json_data = spreadsheetforms.api.get_data_from_form(
                guide_file,
                request.FILES["file"].temporary_file_path(),
                date_format=getattr(
                    settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
                ),
            )
            del json_data["id"]

            # process the data in form.cleaned_data as required
            # Save the event
            new_event_data = NewEventData(
                TYPE_FUND_PUBLIC_ID,
                data.public_id,
                json_data,
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_fund_index", kwargs={"public_id": data.public_id},
                )
            )

        # If this is a GET (or any other method) create the default form.
    else:
        form = FundImportForm()

    context = {
        "record": data,
        "form": form,
    }

    return render(request, "indigo/admin/fund/import_form.html", context)


@permission_required("indigo.admin")
def admin_funds_new(request):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")

    # If this is a POST request then process the Form data
    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = FundNewForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = form.cleaned_data["id"]
            existing_record = Record.objects.filter(type=type, public_id=id)
            if existing_record:
                form.add_error("id", "This ID already exists")
            else:
                data = NewEventData(
                    type,
                    id,
                    {"name": {"value": form.cleaned_data["name"]}},
                    approved=True,
                )
                newEvent(
                    [data], user=request.user, comment=form.cleaned_data["comment"]
                )

                # redirect to a new URL:
                return HttpResponseRedirect(
                    reverse("indigo_admin_fund_index", kwargs={"public_id": id},)
                )

    # If this is a GET (or any other method) create the default form.
    else:
        form = FundNewForm()

    context = {
        "form": form,
    }

    return render(request, "indigo/admin/fund/new.html", context)


@permission_required("indigo.admin")
def admin_fund_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    edits = Edit.objects.filter(record=record, approval_event=None, refusal_event=None)

    if request.method == "POST":

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

        return HttpResponseRedirect(
            reverse("indigo_admin_fund_index", kwargs={"public_id": public_id},)
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.field_datas = jsondataferret.utils.get_field_list_from_json(
            TYPE_FUND_PUBLIC_ID, edit.data
        )

    return render(
        request,
        "indigo/admin/fund/moderate.html",
        {"type": type, "record": record, "edits": edits},
    )


@permission_required("indigo.admin")
def admin_fund_history(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    events = Event.objects.filter_by_record(record)

    return render(
        request,
        "indigo/admin/fund/history.html",
        {"type": type, "record": record, "events": events},
    )


########################### Admin - Event


@permission_required("indigo.admin")
def admin_event_index(request, event_id):
    try:
        event = Event.objects.get(public_id=event_id)
    except Event.DoesNotExist:
        raise Http404("Event does not exist")
    edits_created = event.edits_created.all()
    edits_approved = event.edits_approved.all()
    edits_refused = event.edits_refused.all()
    edits_created_and_approved = list(set(edits_created).intersection(edits_approved))
    edits_only_created = [
        edit for edit in edits_created if edit not in edits_created_and_approved
    ]
    edits_only_approved = [
        edit for edit in edits_approved if edit not in edits_created_and_approved
    ]
    return render(
        request,
        "indigo/admin/event/index.html",
        {
            "event": event,
            "edits_created": edits_created,
            "edits_approved": edits_approved,
            "edits_refused": edits_refused,
            "edits_only_created": edits_only_created,
            "edits_only_approved": edits_only_approved,
            "edits_created_and_approved": edits_created_and_approved,
        },
    )
