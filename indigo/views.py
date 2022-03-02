import csv
import os
import random
import tempfile

import jsondataferret
import jsondataferret.utils
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.files.storage import default_storage
from django.db.models.functions import Now
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from jsondataferret.models import Edit, Event, Record, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.processdata
import indigo.utils
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.dataqualityreport import (
    DataQualityReportForProject,
    get_single_field_statistics_across_all_projects_for_field,
)
from indigo.tasks import task_process_imported_project_file

from .forms import (
    AssessmentResourceNewForm,
    FundNewForm,
    ModelImportForm,
    OrganisationImportForm,
    OrganisationNewForm,
    ProjectImportForm,
    ProjectImportStage2Form,
    ProjectMakeDisputedForm,
    ProjectMakePrivateForm,
    ProjectNewForm,
    RecordChangeStatusForm,
)
from .models import (
    AssessmentResource,
    Fund,
    Organisation,
    Project,
    ProjectImport,
    Sandbox,
)
from .spreadsheetforms import (
    convert_assessment_resource_data_to_spreadsheetforms_data,
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
    extract_edits_from_assessment_resource_spreadsheet,
    extract_edits_from_fund_spreadsheet,
    extract_edits_from_organisation_spreadsheet,
    extract_edits_from_project_spreadsheet,
)

########################### Home Page


def index(request):
    return render(request, "indigo/index.html")


########################### Public - Project


def projects_list(request):
    projects = Project.objects.filter(exists=True, status_public=True).order_by(
        "public_id"
    )
    return render(request, "indigo/projects.html", {"projects": projects},)


def projects_list_download(request):
    projects = Project.objects.filter(exists=True, status_public=True).order_by(
        "public_id"
    )
    return _projects_list_download_worker(projects)


def projects_list_download_social_investment_prototype(request):
    projects = Project.objects.filter(
        exists=True, status_public=True, social_investment_prototype=True
    ).order_by("public_id")
    return _projects_list_download_worker(projects)


def _projects_list_download_worker(projects):

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="projects.csv"'

    labels = ["ID"]
    keys = []
    for config in settings.JSONDATAFERRET_TYPE_INFORMATION["project"]["fields"]:
        if config.get("type", "") != "list" and config.get("key").find("/status") == -1:
            labels.append(config.get("title"))
            keys.append(config.get("key"))
    labels.append("Organisations")
    labels.append("Countries")

    writer = csv.writer(response)
    writer.writerow(labels)
    for project in projects:
        # id
        row = [project.public_id]
        # fields
        for key in keys:
            try:
                row.append(jsonpointer.resolve_pointer(project.data_public, key))
            except jsonpointer.JsonPointerException:
                row.append("")
        # orgs
        orgs_list = jsonpointer.resolve_pointer(
            project.data_public, "/organisations", []
        )
        if isinstance(orgs_list, list):
            orgs = [jsonpointer.resolve_pointer(d, "/id", "") for d in orgs_list]
            row.append(", ".join([i for i in orgs if isinstance(i, str) and i]))
        else:
            row.append("")

        # Countries
        delivery_locations_list = jsonpointer.resolve_pointer(
            project.data_public, "/delivery_locations", []
        )
        if isinstance(delivery_locations_list, list):
            delivery_locations = [
                jsonpointer.resolve_pointer(d, "/location_country/value", "")
                for d in delivery_locations_list
            ]
            # List/set removes duplicates
            row.append(
                ", ".join(
                    list(
                        set([i for i in delivery_locations if isinstance(i, str) and i])
                    )
                )
            )
        else:
            row.append("")

        # project done
        writer.writerow(row)

    return response


def project_download_blank_form(request):
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    guide_file = settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
        "spreadsheet_public_form_guide"
    ]
    spreadsheetforms.api.make_empty_form(guide_file, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=project.xlsx"

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

    data = convert_project_data_to_spreadsheetforms_data(project, public_only=True)
    guide_file = settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
        "spreadsheet_public_form_guide"
    ]
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


########################### Public - Organisation


def organisations_list(request):
    organisations = Organisation.objects.filter(
        exists=True, status_public=True
    ).order_by("public_id")
    return render(
        request, "indigo/organisations.html", {"organisations": organisations},
    )


def organisation_download_blank_form(request):
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    guide_file = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "spreadsheetform_guides",
        "organisation_public_v003.xlsx",
    )
    spreadsheetforms.api.make_empty_form(guide_file, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=organisation.xlsx"

    return response


def organisation_index(request, public_id):
    try:
        organisation = Organisation.objects.get(
            exists=True, status_public=True, public_id=public_id
        )
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    if not organisation.status_public or not organisation.exists:
        raise Http404("Organisation does not exist")
    field_data = jsondataferret.utils.get_field_list_from_json(
        TYPE_ORGANISATION_PUBLIC_ID, organisation.data_public
    )
    return render(
        request,
        "indigo/organisation/index.html",
        {"organisation": organisation, "field_data": field_data},
    )


def organisation_download_form(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    if not organisation.status_public or not organisation.exists:
        raise Http404("Organisation does not exist")

    data = convert_organisation_data_to_spreadsheetforms_data(
        organisation, public_only=True
    )
    guide_file = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "spreadsheetform_guides",
        "organisation_public_v003.xlsx",
    )
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = (
            "inline; filename=organisation" + organisation.public_id + ".xlsx"
        )
    return response


########################### Public - For Multiple Models
# To try and reduce repeated code in very similar views, we move views to the classes below as we work on them.


class ModelList(View):
    def get(self, request):
        datas = self.__class__._model.objects.filter(
            exists=True, status_public=True
        ).order_by("public_id")
        return render(
            request,
            "indigo/" + self.__class__._model.__name__.lower() + "s.html",
            {"datas": datas},
        )


class FundList(ModelList):
    _model = Fund


class AssessmentResourceList(ModelList):
    _model = AssessmentResource


class ModelListDownload(View):
    def get(self, request):
        datas = self.__class__._model.objects.filter(
            exists=True, status_public=True
        ).order_by("public_id")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="' + self.__class__._model.type_id + 's.csv"'
        )

        labels = ["ID"]
        keys = []

        for config in settings.JSONDATAFERRET_TYPE_INFORMATION[
            self.__class__._model.type_id
        ]["fields"]:
            if (
                config.get("type", "") != "list"
                # We don't want Organisation contact details
                and config.get("key").find("/contact") == -1
            ):
                labels.append(config.get("title"))
                keys.append(config.get("key"))

        writer = csv.writer(response)
        writer.writerow(labels)
        for data in datas:
            row = [data.public_id]
            for key in keys:
                try:
                    row.append(jsonpointer.resolve_pointer(data.data_public, key))
                except jsonpointer.JsonPointerException:
                    row.append("")
            writer.writerow(row)

        return response


class FundListDownload(ModelListDownload):
    _model = Fund


class OrganisationListDownload(ModelListDownload):
    _model = Organisation


class ModelIndex(View):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(
                exists=True, status_public=True, public_id=public_id
            )
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        if not data.status_public or not data.exists:
            raise Http404("Data does not exist")
        field_data = jsondataferret.utils.get_field_list_from_json(
            self.__class__._type_public_id, data.data_public
        )
        return render(
            request,
            "indigo/" + self.__class__._model.__name__.lower() + "/index.html",
            {"data": data, "field_data": field_data},
        )


class FundIndex(ModelIndex):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AssessmentResourceIndex(ModelIndex):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class ModelDownloadForm(View):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(
                exists=True, status_public=True, public_id=public_id
            )
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        if not data.status_public or not data.exists:
            raise Http404("Data does not exist")

        data_for_spreadsheet = self.__class__._convert_function(data, public_only=True)
        guide_file = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "spreadsheetform_guides",
            self.__class__._spreadsheet_file_name,
        )
        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )
        spreadsheetforms.api.put_data_in_form(
            guide_file, data_for_spreadsheet, out_file
        )

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + data.__class__.__name__ + data.public_id + ".xlsx"
            )
        return response


class FundDownloadForm(ModelDownloadForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _spreadsheet_file_name = "fund_public_v001.xlsx"
    _convert_function = convert_fund_data_to_spreadsheetforms_data


########################### Public - All


def all_public_data_file_per_record_in_zip(request):
    if default_storage.exists("public/all_data_as_spreadsheets.zip"):
        wrapper = default_storage.open("public/all_data_as_spreadsheets.zip")
        response = HttpResponse(wrapper, content_type="application/zip")
        response[
            "Content-Disposition"
        ] = "attachment; filename=all_data_as_spreadsheets.zip"
        return response


def all_public_data_file_per_data_type_csv_in_zip(request):
    if default_storage.exists("public/all_data_per_data_type_csv.zip"):
        wrapper = default_storage.open("public/all_data_per_data_type_csv.zip")
        response = HttpResponse(wrapper, content_type="application/zip")
        response[
            "Content-Disposition"
        ] = "attachment; filename=all_data_per_data_type_csv.zip"
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
    if (
        settings.API_SANDBOX_DATA_PASSWORD
        and request.GET.get("sandbox_data_password", "")
        == settings.API_SANDBOX_DATA_PASSWORD
    ):
        data["project"]["sandboxes"] = project.data_sandboxes
    return JsonResponse(data)


########################### Public - Organisation - API


def api1_organisations_list(request):
    organisations = Organisation.objects.filter()
    data = {
        "organisations": [
            {"id": p.public_id, "public": (p.exists and p.status_public)}
            for p in organisations
        ]
    }
    return JsonResponse(data)


def api1_organisation_index(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    if not organisation.status_public or not organisation.exists:
        raise Http404("Organisation does not exist")

    data = {
        "organisation": {
            "id": organisation.public_id,
            "data": organisation.data_public,
        }
    }
    return JsonResponse(data)


########################### Public - Fund & Assesment Resource - API


class API1ModelList(View):
    def get(self, request):
        datas = self.__class__._model.objects.filter().order_by("public_id")
        output = {
            self.__class__._model.type_id
            + "s": [
                {"id": d.public_id, "public": (d.exists and d.status_public)}
                for d in datas
            ]
        }
        return JsonResponse(output)


class API1FundList(API1ModelList):
    _model = Fund


class API1AssessmentResourceList(API1ModelList):
    _model = AssessmentResource


class API1ModelIndex(View):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(
                exists=True, status_public=True, public_id=public_id
            )
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        if not data.status_public or not data.exists:
            raise Http404("Data does not exist")
        data = {
            self.__class__._model.type_id: {
                "id": data.public_id,
                "data": data.data_public,
            }
        }
        return JsonResponse(data)


class API1FundIndex(API1ModelIndex):
    _model = Fund


class API1AssessmentResourceIndex(API1ModelIndex):
    _model = AssessmentResource


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
    projects = Record.objects.filter(type=type).order_by("public_id")
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
    type_data = settings.JSONDATAFERRET_TYPE_INFORMATION.get(TYPE_PROJECT_PUBLIC_ID, {})
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")

    data = convert_project_data_to_spreadsheetforms_data(project, public_only=False)
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.put_data_in_form(
        type_data.get("spreadsheet_form_guide"), data, out_file
    )

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

            # Save the data
            project_import = ProjectImport()
            project_import.user = request.user
            project_import.project = project
            with open(request.FILES["file"].temporary_file_path(), "rb") as fp:
                project_import.file_data = fp.read()
            project_import.save()

            # Make celery call to start background worker
            task_process_imported_project_file.delay(project_import.id)

            # redirect to a new URL so user can wait for stage 2 of the process to be ready
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

    if project_import.exception:
        return render(
            request,
            "indigo/admin/project/import_form_stage_2_exception.html",
            {"record": record, "project": project, "import": project_import},
        )

    if project_import.file_not_valid:
        return render(
            request,
            "indigo/admin/project/import_form_stage_2_file_not_valid.html",
            {"record": record, "project": project},
        )

    if not project_import.data:
        return render(
            request,
            "indigo/admin/project/import_form_stage_2_wait.html",
            {"record": record, "project": project, "import": project_import},
        )

    data_quality_report = DataQualityReportForProject(project_import.data)
    level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = ProjectImportStage2Form(request.POST, request.FILES)

        # Check if the form is valid:
        if form.is_valid():

            # process the data as required
            # Save the event
            new_event_datas = extract_edits_from_project_spreadsheet(
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

            # redirect to project page with message
            messages.add_message(
                request,
                messages.INFO,
                "The data has been imported; remember to moderate it!",
            )
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
        "level_zero_errors": level_zero_errors,
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


@permission_required("indigo.admin")
def admin_project_data_quality_report(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")

    dqr = DataQualityReportForProject(project.record.cached_data)

    return render(
        request,
        "indigo/admin/project/data_quality_report.html",
        {
            "project": project,
            "record": project.record,
            "data_quality_report": dqr,
            "errors_by_priority_level": dqr.get_errors_in_priority_levels(),
        },
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report(request):

    return render(
        request,
        "indigo/admin/projects_data_quality_report.html",
        {
            "fields_single": [
                i
                for i in settings.JSONDATAFERRET_TYPE_INFORMATION["project"]["fields"]
                if i.get("type") != "list"
            ],
        },
    )


@permission_required("indigo.admin")
def admin_all_projects_data_quality_report_field_single(request):

    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    fields = [
        i
        for i in settings.JSONDATAFERRET_TYPE_INFORMATION["project"]["fields"]
        if i.get("type") != "list" and i.get("key") == field_path
    ]
    if not fields:
        raise Http404("Field does not exist")  #
    field = fields[0]

    data = {"field": field}
    data.update(get_single_field_statistics_across_all_projects_for_field(field))

    return render(
        request, "indigo/admin/projects_data_quality_report_single_field.html", data,
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
    return render(request, "indigo/admin/organisations.html", {},)


@permission_required("indigo.admin")
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


@permission_required("indigo.admin")
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
        "indigo/admin/organisations_search.html",
        {"search_term": search_term, "organisations": organisations},
    )


@permission_required("indigo.admin")
def admin_organisation_download_all_csv(request):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    organisations = Record.objects.filter(type=type).order_by("public_id")

    response = HttpResponse(content_type="text/csv")
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
def admin_organisation_change_status(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = RecordChangeStatusForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():

            # Save the event
            new_event_data = NewEventData(
                type,
                record,
                {"status": form.cleaned_data["status"]},
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            messages.add_message(
                request, messages.INFO, "Done; remember to moderate it!",
            )
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_index",
                    kwargs={"public_id": record.public_id},
                )
            )

    else:

        form = RecordChangeStatusForm()

    context = {
        "record": record,
        "form": form,
    }

    return render(request, "indigo/admin/organisation/change_status.html", context,)


@permission_required("indigo.admin")
def admin_organisation_projects(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return render(
        request,
        "indigo/admin/organisation/projects.html",
        {
            "organisation": organisation,
            "project_links": organisation.included_by_projects.all(),
        },
    )


@permission_required("indigo.admin")
def admin_organisation_download_form(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")

    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "organisation_v004.xlsx",
    )

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    data = convert_organisation_data_to_spreadsheetforms_data(
        organisation, public_only=False
    )

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


########################### Admin - funds & assessment resources


class AdminModelDownloadBlankForm(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request):
        type_data = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
            self.__class__._type_public_id, {}
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
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response


class AdminFundDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AdminAssessmentResourceDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class AdminModelList(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        datas = Record.objects.filter(type=type).order_by("public_id")
        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "s.html",
            {"datas": datas},
        )


class AdminFundList(AdminModelList):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AdminAssessmentResourceList(AdminModelList):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class AdminModelIndex(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        field_data = jsondataferret.utils.get_field_list_from_json(
            self.__class__._model.type_id, data.data_private
        )
        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/index.html",
            {"data": data, "field_data": field_data},
        )


class AdminFundIndex(AdminModelIndex):
    _model = Fund


class AdminAssessmentResourceIndex(AdminModelIndex):
    _model = AssessmentResource


@permission_required("indigo.admin")
def admin_fund_projects(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    return render(
        request,
        "indigo/admin/fund/projects.html",
        {"fund": fund, "project_links": fund.included_by_projects.all(),},
    )


class AdminModelDownloadForm(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        guide_file = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "spreadsheetform_guides",
            self.__class__._guide_file_name,
        )

        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )

        data_for_form = self._get_data_for_form(data)

        spreadsheetforms.api.put_data_in_form(guide_file, data_for_form, out_file)

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response


class AdminFundDownloadForm(AdminModelDownloadForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = "fund_v003.xlsx"

    def _get_data_for_form(self, data):
        return convert_fund_data_to_spreadsheetforms_data(data, public_only=False)


class AdminAssessmentResourceDownloadForm(AdminModelDownloadForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = "assessment_resource_v001.xlsx"

    def _get_data_for_form(self, data):
        return convert_assessment_resource_data_to_spreadsheetforms_data(
            data, public_only=False
        )


class AdminModelImportForm(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        form = self.__class__._form_class()
        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/import_form.html",
            {"data": data, "form": form,},
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
                    self.__class__._redirect_view, kwargs={"public_id": data.public_id},
                )
            )
        else:
            return render(
                request,
                "indigo/admin/"
                + self.__class__._model.__name__.lower()
                + "/import_form.html",
                {"data": data, "form": form,},
            )


class AdminFundImportForm(AdminModelImportForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = ModelImportForm
    _redirect_view = "indigo_admin_fund_index"

    def _get_edits(self, data, import_json):
        return extract_edits_from_fund_spreadsheet(data.record, import_json)


class AdminAssessmentResourceImportForm(AdminModelImportForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = ModelImportForm
    _redirect_view = "indigo_admin_assessment_resource_index"

    def _get_edits(self, data, import_json):
        return extract_edits_from_assessment_resource_spreadsheet(
            data.record, import_json
        )


class AdminModelNew(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request):
        form = self.__class__._form_class()
        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/new.html",
            {"form": form,},
        )

    def post(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        form = self.__class__._form_class(request.POST)
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
                    reverse(self.__class__._redirect_view, kwargs={"public_id": id},)
                )

        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/new.html",
            {"form": form,},
        )


class AdminFundNew(AdminModelNew):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = FundNewForm
    _redirect_view = "indigo_admin_fund_index"


class AdminAssessmentResourceNew(AdminModelNew):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = AssessmentResourceNewForm
    _redirect_view = "indigo_admin_assessment_resource_index"


class AdminModelModerate(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

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

        if request.method == "POST":

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
                return HttpResponseRedirect(
                    reverse(
                        self.__class__._redirect_view,
                        kwargs={"public_id": record.public_id},
                    )
                )

        for edit in edits:
            # TODO This will not take account of data_key on an edit If we start using that we will need to check this
            edit.field_datas = jsondataferret.utils.get_field_list_from_json(
                self.__class__._model.type_id, edit.data
            )

        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/moderate.html",
            {"type": type, "record": record, "edits": edits},
        )


class AdminFundModerate(AdminModelModerate):
    _model = Fund
    _redirect_view = "indigo_admin_fund_index"


class AdminAssessmentResourceModerate(AdminModelModerate):
    _model = AssessmentResource
    _redirect_view = "indigo_admin_assessment_resource_index"


class AdminModelHistory(PermissionRequiredMixin, View):
    permission_required = "indigo.admin"

    def get(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        events = Event.objects.filter_by_record(record)

        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/history.html",
            {"type": type, "record": record, "events": events},
        )


class AdminFundHistory(AdminModelHistory):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AdminAssessmentResourceHistory(AdminModelHistory):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


########################### Admin - sandboxes


@permission_required("indigo.admin")
def admin_sandbox_list(request):
    sandboxes = Sandbox.objects.all()
    return render(request, "indigo/admin/sandboxes.html", {"sandboxes": sandboxes},)


@permission_required("indigo.admin")
def admin_sandbox_index(request, public_id):
    try:
        sandbox = Sandbox.objects.get(public_id=public_id)
    except Sandbox.DoesNotExist:
        raise Http404("Sandbox does not exist")
    return render(request, "indigo/admin/sandbox/index.html", {"sandbox": sandbox},)


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
