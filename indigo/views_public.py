import csv
import os
import random
import tempfile
from abc import ABC

import jsondataferret
import jsondataferret.utils
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)

from .models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    Project,
)
from .spreadsheetforms import (
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_pipeline_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
)

########################### Home Page


def index(request):
    return render(request, "indigo/index.html")


########################### Public - Project


def projects_list(request):
    projects = Project.objects.filter(exists=True, status_public=True).order_by(
        "public_id"
    )
    return render(
        request,
        "indigo/projects.html",
        {"projects": projects},
    )


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

    response = HttpResponse(content_type="text/csv; charset=utf-8")
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


def project_download_data_quality_report(request):
    if default_storage.exists("public/project_data_quality_report.xlsx"):
        wrapper = default_storage.open("public/project_data_quality_report.xlsx")
        response = HttpResponse(wrapper, content_type="application/vnd.ms-excel")
        response[
            "Content-Disposition"
        ] = "inline; filename=data_quality_report_on_all_projects.xlsx"
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
        request,
        "indigo/organisations.html",
        {"organisations": organisations},
    )


def organisation_download_blank_form(request):
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.make_empty_form(
        settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
            "spreadsheet_public_form_guide"
        ],
        out_file,
    )

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
    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )
    spreadsheetforms.api.put_data_in_form(
        settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
            "spreadsheet_public_form_guide"
        ],
        data,
        out_file,
    )

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = (
            "inline; filename=organisation" + organisation.public_id + ".xlsx"
        )
    return response


########################### Public - All


def pipeline_public_data_file_per_record_in_zip(request):
    if default_storage.exists("public/pipeline_data_as_spreadsheets.zip"):
        wrapper = default_storage.open("public/pipeline_data_as_spreadsheets.zip")
        response = HttpResponse(wrapper, content_type="application/zip")
        response[
            "Content-Disposition"
        ] = "attachment; filename=pipeline_data_as_spreadsheets.zip"
        return response


def pipeline_public_data_file_per_data_type_csv_in_zip(request):
    if default_storage.exists("public/pipeline_data_per_data_type_csv.zip"):
        wrapper = default_storage.open("public/pipeline_data_per_data_type_csv.zip")
        response = HttpResponse(wrapper, content_type="application/zip")
        response[
            "Content-Disposition"
        ] = "attachment; filename=pipeline_data_per_data_type_csv.zip"
        return response


########################### Public - For Multiple Models
# To try and reduce repeated code in very similar views, we move views to the classes below as we work on them.


class ModelList(View, ABC):
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


class PipelineList(ModelList):
    _model = Pipeline


class JoiningUpInitiativeList(ModelList):
    _model = JoiningUpInitiative


class ModelListDownload(View, ABC):
    def get(self, request):
        datas = self.__class__._model.objects.filter(
            exists=True, status_public=True
        ).order_by("public_id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
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
                # All data is public anyway, so status fields are pointless
                and config.get("key").find("/status") == -1
            ):
                labels.append(config.get("title"))
                keys.append(config.get("key"))

        labels.extend(self._get_extra_headers())

        writer = csv.writer(response)
        writer.writerow(labels)
        for data in datas:
            row = [data.public_id]
            for key in keys:
                try:
                    row.append(jsonpointer.resolve_pointer(data.data_public, key))
                except jsonpointer.JsonPointerException:
                    row.append("")
            row.extend(self._get_extra_data(data))
            writer.writerow(row)

        return response

    def _get_extra_headers(self):
        return []

    def _get_extra_data(self, data):
        return []


class FundListDownload(ModelListDownload):
    _model = Fund


class OrganisationListDownload(ModelListDownload):
    _model = Organisation


class PipelineListDownload(ModelListDownload):
    _model = Pipeline

    def _get_extra_headers(self):
        return ["Delivery Locations - Name", "Delivery Locations - Country"]

    def _get_extra_data(self, data):
        delivery_locations_list = jsonpointer.resolve_pointer(
            data.data_public, "/delivery_locations", []
        )
        if isinstance(delivery_locations_list, list):
            delivery_location_names = [
                jsonpointer.resolve_pointer(d, "/location_name/value", "")
                for d in delivery_locations_list
            ]
            delivery_location_country_codes = [
                jsonpointer.resolve_pointer(d, "/location_country/value", "")
                for d in delivery_locations_list
            ]
            # List/set removes duplicates
            return [
                ", ".join(
                    list(
                        set(
                            [
                                i
                                for i in delivery_location_names
                                if isinstance(i, str) and i
                            ]
                        )
                    )
                ),
                ", ".join(
                    list(
                        set(
                            [
                                i
                                for i in delivery_location_country_codes
                                if isinstance(i, str) and i
                            ]
                        )
                    )
                ),
            ]
        else:
            return []


class ModelIndex(View, ABC):
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


class PipelineIndex(ModelIndex):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID


class JoiningUpInitiativeIndex(ModelIndex):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID


class ModelDownloadForm(View, ABC):
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


class PipelineDownloadForm(ModelDownloadForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _spreadsheet_file_name = "pipeline_public_v001.xlsx"
    _convert_function = convert_pipeline_data_to_spreadsheetforms_data


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


def all_public_data_sqlite(request):
    if default_storage.exists("public/all_data.sqlite"):
        wrapper = default_storage.open("public/all_data.sqlite")
        response = HttpResponse(wrapper, content_type="application/vnd.sqlite3")
        response["Content-Disposition"] = "attachment; filename=all_data.sqlite"
        return response
