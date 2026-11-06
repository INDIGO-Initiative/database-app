import csv
import os
import random
import tempfile
from abc import ABC

import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views import View

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)

from .listpages import list_context, search_filter, visible_menu
from .recordpages import build_record_sections
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


def _breadcrumbs(*crumbs):
    """The trail shown under the top bar: Home, then each of the crumbs (label, url name or None for the current page)."""
    return [{"label": "Home", "url": reverse("indigo_index")}] + [
        {"label": label, "url": reverse(url_name) if url_name else None}
        for label, url_name in crumbs
    ]


def _public_list(
    request,
    model,
    *,
    title,
    noun_plural,
    url_prefix,
    items_key,
    search_keys,
    menu_groups=None,
):
    """A public list page: only records that are public, with a search that only looks at public data."""
    records = model.objects.filter(exists=True, status_public=True).order_by(
        "public_id"
    )
    search_term = request.GET.get("search", "").strip()
    if search_term:
        # Search the public data only, so a search can never find something that is private
        records = records.filter(search_filter(search_term, "data_public", search_keys))
    return render(
        request,
        "indigo/list.html",
        list_context(
            request,
            records,
            title=title,
            noun_plural=noun_plural,
            name_field="data_public",
            index_url_name=f"indigo_{url_prefix}_index",
            list_url_name=f"indigo_{url_prefix}_list",
            items_key=items_key,
            search_term=search_term,
            searchable=True,
            search_placeholder="ID or name",
            menu_groups=menu_groups,
            menu_label="Download",
            menu_icon="download",
            breadcrumbs=_breadcrumbs((title, None)),
        ),
    )


def _downloads(*items):
    """A Download menu from (label, url name) or (label, url name, url kwargs) tuples."""
    return [
        {
            "heading": None,
            "items": [
                {
                    "label": item[0],
                    "url_name": item[1],
                    **({"url_kwargs": item[2]} if len(item) > 2 else {}),
                }
                for item in items
            ],
        }
    ]


def _public_record(
    request,
    record,
    *,
    record_title,
    type_public_id,
    url_prefix,
    list_title,
    has_download_form=True,
):
    """A public record page: the record's public fields, with a Download menu."""
    kwargs = {"public_id": record.public_id}
    downloads = []
    if has_download_form:
        downloads.append(
            ("Download Form", f"indigo_{url_prefix}_download_form", kwargs)
        )
    downloads.append(("JSON data", f"indigo_api1_{url_prefix}_index", kwargs))
    name = (record.data_public or {}).get("name")
    return render(
        request,
        "indigo/record.html",
        {
            "record": record,
            "record_title": record_title,
            "display_name": name.get("value", "") if isinstance(name, dict) else "",
            "sections": build_record_sections(type_public_id, record.data_public),
            "menu": visible_menu(request.user, _downloads(*downloads)),
            "menu_label": "Download",
            "menu_icon": "download",
            "breadcrumbs": _breadcrumbs(
                (list_title, f"indigo_{url_prefix}_list"), (record.public_id, None)
            ),
        },
    )


########################### Home Page


def index(request):
    def public_count(model):
        # The same records the public lists show
        return model.objects.filter(exists=True, status_public=True).count()

    sections = [
        {
            "title": "Projects",
            "icon": "diagram-project",
            "count": public_count(Project),
            "list_url": "indigo_project_list",
            "api_url": "indigo_api1_project_list",
        },
        {
            "title": "Organisations",
            "icon": "building",
            "count": public_count(Organisation),
            "list_url": "indigo_organisation_list",
            "api_url": "indigo_api1_organisation_list",
        },
        {
            "title": "Funds",
            "icon": "coins",
            "count": public_count(Fund),
            "list_url": "indigo_fund_list",
            "api_url": "indigo_api1_fund_list",
        },
        {
            "title": "Pipelines",
            "icon": "bars-progress",
            "count": public_count(Pipeline),
            "list_url": "indigo_pipeline_list",
            "api_url": "indigo_api1_pipeline_list",
        },
        {
            "title": "Assessment Resources",
            "icon": "clipboard-check",
            "count": public_count(AssessmentResource),
            "list_url": "indigo_assessment_resource_list",
            "api_url": "indigo_api1_assessment_resource_list",
        },
        {
            "title": "Joining Up Initiatives",
            "icon": "handshake",
            "count": public_count(JoiningUpInitiative),
            "list_url": "indigo_joining_up_initiative_list",
            "api_url": "indigo_api1_joining_up_initiative_list",
        },
    ]
    return render(request, "indigo/index.html", {"sections": sections})


########################### Public - Project


def projects_list(request):
    return _public_list(
        request,
        Project,
        title="Projects",
        noun_plural="projects",
        url_prefix="project",
        items_key="projects",
        search_keys=["name", "alternative_names"],
        menu_groups=_downloads(
            ("Download List (All)", "indigo_project_list_download"),
            (
                "Download List (Social Investment Prototype)",
                "indigo_project_list_download_social_investment_prototype",
            ),
            ("Download Blank Form", "indigo_project_download_blank_form"),
            (
                "Download Data Quality Report",
                "indigo_project_download_data_quality_report",
            ),
        ),
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
    return _public_record(
        request,
        project,
        record_title="Project",
        type_public_id=TYPE_PROJECT_PUBLIC_ID,
        url_prefix="project",
        list_title="Projects",
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
    return _public_list(
        request,
        Organisation,
        title="Organisations",
        noun_plural="organisations",
        url_prefix="organisation",
        items_key="organisations",
        search_keys=["name"],
        menu_groups=_downloads(
            ("Download List", "indigo_organisation_list_download"),
            ("Download Blank Form", "indigo_organisation_download_blank_form"),
        ),
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
    return _public_record(
        request,
        organisation,
        record_title="Organisation",
        type_public_id=TYPE_ORGANISATION_PUBLIC_ID,
        url_prefix="organisation",
        list_title="Organisations",
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
    """A public list of records of one type. Each list says (in its class variables):

    _list_title / _noun_plural: the words to use
    _url_prefix: the start of its view names, eg "fund" for indigo_fund_index
    _search_keys: the keys of the (public) data whose value can be searched, as well as the ID
    _menu_groups: what goes in the Download menu"""

    _search_keys = ["name"]
    _menu_groups = None

    def get(self, request):
        cls = self.__class__
        return _public_list(
            request,
            cls._model,
            title=cls._list_title,
            noun_plural=cls._noun_plural,
            url_prefix=cls._url_prefix,
            items_key="datas",
            search_keys=cls._search_keys,
            menu_groups=cls._menu_groups,
        )


class FundList(ModelList):
    _model = Fund
    _list_title = "Funds"
    _noun_plural = "funds"
    _url_prefix = "fund"
    _menu_groups = _downloads(("Download List", "indigo_fund_list_download"))


class AssessmentResourceList(ModelList):
    _model = AssessmentResource
    _list_title = "Assessment Resources"
    _noun_plural = "assessment resources"
    _url_prefix = "assessment_resource"


class PipelineList(ModelList):
    _model = Pipeline
    _list_title = "Pipelines"
    _noun_plural = "pipelines"
    _url_prefix = "pipeline"
    _search_keys = ["name", "alternative_names"]
    _menu_groups = _downloads(
        ("Download List", "indigo_pipeline_list_download"),
        (
            "Download data (Zip File of Spreadsheets, one per record)",
            "indigo_pipeline_public_data_file_per_record_in_zip",
        ),
        (
            "Download data (Zip File of CSVs, one per data type)",
            "indigo_pipeline_public_data_file_per_data_type_csv_in_zip",
        ),
    )


class JoiningUpInitiativeList(ModelList):
    _model = JoiningUpInitiative
    _list_title = "Joining Up Initiatives"
    _noun_plural = "Joining Up Initiatives"
    _url_prefix = "joining_up_initiative"


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
    """The public page of one record of a type. Each says (in its class variables):

    _record_title: what to call one of them
    _list_title / _url_prefix: how to link back to its list, and the start of its view names
    _has_download_form: whether there is a spreadsheet form to download for it"""

    _has_download_form = True

    def get(self, request, public_id):
        cls = self.__class__
        try:
            data = cls._model.objects.get(
                exists=True, status_public=True, public_id=public_id
            )
        except cls._model.DoesNotExist:
            raise Http404("Data does not exist")
        if not data.status_public or not data.exists:
            raise Http404("Data does not exist")
        return _public_record(
            request,
            data,
            record_title=cls._record_title,
            type_public_id=cls._type_public_id,
            url_prefix=cls._url_prefix,
            list_title=cls._list_title,
            has_download_form=cls._has_download_form,
        )


class FundIndex(ModelIndex):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _record_title = "Fund"
    _list_title = FundList._list_title
    _url_prefix = FundList._url_prefix


class AssessmentResourceIndex(ModelIndex):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _record_title = "Assessment Resource"
    _list_title = AssessmentResourceList._list_title
    _url_prefix = AssessmentResourceList._url_prefix
    _has_download_form = False


class PipelineIndex(ModelIndex):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _record_title = "Pipeline"
    _list_title = PipelineList._list_title
    _url_prefix = PipelineList._url_prefix


class JoiningUpInitiativeIndex(ModelIndex):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _record_title = "Joining Up Initiative"
    _list_title = JoiningUpInitiativeList._list_title
    _url_prefix = JoiningUpInitiativeList._url_prefix
    _has_download_form = False


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
    _spreadsheet_file_name = "pipeline_public_v002.xlsx"
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
