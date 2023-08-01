import csv
import os
import random
import tempfile
import urllib.parse
from abc import ABC

import jsondataferret
import jsondataferret.utils
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models.functions import Now
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from jsondataferret.filters import EventFilter
from jsondataferret.models import CachedRecordHistory, Edit, Event, Record, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.processdata
import indigo.utils
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.dataqualityreport import (
    DataQualityReportForAllProjects,
    DataQualityReportForPipeline,
    DataQualityReportForProject,
)
from indigo.tasks import (
    task_process_imported_pipeline_file,
    task_process_imported_project_file,
)

from .forms import (
    AssessmentResourceNewForm,
    FundNewForm,
    JoiningUpInitiativeEditForm,
    JoiningUpInitiativeNewForm,
    ModelImportForm,
    ModelImportStage1Of2Form,
    ModelImportStage2Of2Form,
    OrganisationImportForm,
    OrganisationNewForm,
    PipelineNewForm,
    ProjectNewForm,
    RecordChangeStatusForm,
)
from .models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    PipelineImport,
    Project,
    ProjectImport,
    Sandbox,
)
from .spreadsheetforms import (
    convert_assessment_resource_data_to_spreadsheetforms_data,
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_pipeline_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
    extract_edits_from_assessment_resource_spreadsheet,
    extract_edits_from_fund_spreadsheet,
    extract_edits_from_joining_up_initiative_form,
    extract_edits_from_organisation_spreadsheet,
    extract_edits_from_pipeline_spreadsheet,
    extract_edits_from_project_spreadsheet,
)


def _permission_admin_or_data_steward_required_test(user):
    return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


def permission_admin_or_data_steward_required():
    return user_passes_test(_permission_admin_or_data_steward_required_test)


@permission_admin_or_data_steward_required()
def admin_index(request):
    return render(request, "indigo/admin/index.html")


@permission_admin_or_data_steward_required()
def admin_history(request):
    filter = EventFilter(request.GET, queryset=Event.objects.all().order_by("created"))
    paginator = Paginator(filter.qs, 100)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    pagination_get_params = urllib.parse.urlencode(filter.get_get_params_for_paging())
    return render(
        request,
        "indigo/admin/history.html",
        {
            "page_obj": page_obj,
            "filter": filter,
            "pagination_get_params": pagination_get_params,
        },
    )


########################### Admin - Projects


@permission_admin_or_data_steward_required()
def admin_projects_list(request):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    projects = Record.objects.filter(type=type).order_by("public_id")
    return render(
        request,
        "indigo/admin/projects.html",
        {"projects": projects},
    )


@permission_admin_or_data_steward_required()
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

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_project_index",
                    kwargs={"public_id": id},
                )
            )

    # If this is a GET (or any other method) create the default form.
    else:
        form = ProjectNewForm()

    context = {
        "form": form,
    }

    return render(request, "indigo/admin/project/new.html", context)


@permission_admin_or_data_steward_required()
def admin_project_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

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

        return HttpResponseRedirect(
            reverse(
                "indigo_admin_project_index",
                kwargs={"public_id": public_id},
            )
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


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
def admin_all_projects_data_quality_report(request):
    data_quality_report = DataQualityReportForAllProjects()
    return render(
        request,
        "indigo/admin/projects_data_quality_report.html",
        {
            "fields_single": data_quality_report.get_possible_fields_for_single_field_statistics(),
            "fields_list": data_quality_report.get_possible_fields_for_list_field_statistics(),
        },
    )


@permission_admin_or_data_steward_required()
def admin_all_projects_data_quality_report_field_single(request):

    data_quality_report = DataQualityReportForAllProjects()

    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    fields = [
        i
        for i in data_quality_report.get_possible_fields_for_single_field_statistics()
        if i.get("key") == field_path
    ]
    if not fields:
        raise Http404("Field does not exist")  #
    field = fields[0]

    data = {"field": field}
    data.update(data_quality_report.get_single_field_statistics_for_field(field))

    return render(
        request,
        "indigo/admin/projects_data_quality_report_single_field.html",
        data,
    )


@permission_admin_or_data_steward_required()
def admin_all_projects_data_quality_report_field_list(request):

    data_quality_report = DataQualityReportForAllProjects()

    field_path = request.GET.get("field", "")
    # Note we MUST explicitly check the field the user passed is in our pre-calculated Config list!
    # If we don't, we open ourselves up to SQL Injection security holes.
    fields = [
        i
        for i in data_quality_report.get_possible_fields_for_list_field_statistics()
        if i.get("key") == field_path
    ]
    if not fields:
        raise Http404("Field does not exist")  #
    field = fields[0]

    data = {"field": field}
    data.update(data_quality_report.get_list_field_statistics_for_field(field))

    return render(
        request,
        "indigo/admin/projects_data_quality_report_list_field.html",
        data,
    )


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
def admin_organisations_list(request):
    return render(
        request,
        "indigo/admin/organisations.html",
        {},
    )


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
def admin_organisation_download_all_csv(request):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    organisations = Record.objects.filter(type=type).order_by("public_id")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
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


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
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


@permission_admin_or_data_steward_required()
def admin_organisation_download_form(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")

    out_file = os.path.join(
        tempfile.gettempdir(),
        "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
    )

    data = convert_organisation_data_to_spreadsheetforms_data(
        organisation, public_only=False
    )

    spreadsheetforms.api.put_data_in_form(
        settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"][
            "spreadsheet_form_guide"
        ],
        data,
        out_file,
    )

    with open(out_file, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = "inline; filename=organisation.xlsx"

    return response


@permission_admin_or_data_steward_required()
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
                missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
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


@permission_admin_or_data_steward_required()
@transaction.atomic
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
            id = indigo.utils.get_next_record_id(type)
            data = NewEventData(
                type,
                id,
                {"name": {"value": form.cleaned_data["name"]}},
                approved=True,
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_index",
                    kwargs={"public_id": id},
                )
            )

    # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationNewForm()

    context = {
        "form": form,
    }

    return render(request, "indigo/admin/organisation/new.html", context)


@permission_admin_or_data_steward_required()
def admin_organisation_moderate(request, public_id):
    try:
        type = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        record = Record.objects.get(type=type, public_id=public_id)
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    except Record.DoesNotExist:
        raise Http404("Record does not exist")

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

        return HttpResponseRedirect(
            reverse(
                "indigo_admin_organisation_index",
                kwargs={"public_id": public_id},
            )
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


@permission_admin_or_data_steward_required()
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


class AdminModelDownloadBlankForm(PermissionRequiredMixin, View, ABC):
    def get(self, request):
        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )

        spreadsheetforms.api.make_empty_form(self._guide_file_name, out_file)

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")


class AdminProjectDownloadBlankSimpleForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")


class AdminFundDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")


class AdminAssessmentResourceDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")


class AdminPipelineDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")


class AdminModelList(PermissionRequiredMixin, View, ABC):
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

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundList(AdminModelList):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AdminAssessmentResourceList(AdminModelList):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class AdminPipelineList(AdminModelList):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID


class AdminJoiningUpInitiativeList(AdminModelList):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID


class AdminModelIndex(PermissionRequiredMixin, View, ABC):
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

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundIndex(AdminModelIndex):
    _model = Fund


class AdminAssessmentResourceIndex(AdminModelIndex):
    _model = AssessmentResource


class AdminPipelineIndex(AdminModelIndex):
    _model = Pipeline


class AdminJoiningUpInitiativeIndex(AdminModelIndex):
    _model = JoiningUpInitiative


@permission_admin_or_data_steward_required()
def admin_fund_projects(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    return render(
        request,
        "indigo/admin/fund/projects.html",
        {
            "fund": fund,
            "project_links": fund.included_by_projects.all(),
        },
    )


class AdminModelDownloadForm(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        out_file = os.path.join(
            tempfile.gettempdir(),
            "indigo" + str(random.randrange(1, 100000000000)) + ".xlsx",
        )

        data_for_form = self._get_data_for_form(data)

        spreadsheetforms.api.put_data_in_form(
            self.__class__._guide_file_name, data_for_form, out_file
        )

        with open(out_file, "rb") as fh:
            response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            response["Content-Disposition"] = (
                "inline; filename=" + self.__class__._model.__name__.lower() + ".xlsx"
            )

        return response

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDownloadForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)


class AdminProjectDownloadSimpleForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)


class AdminFundDownloadForm(AdminModelDownloadForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_fund_data_to_spreadsheetforms_data(data, public_only=False)


class AdminAssessmentResourceDownloadForm(AdminModelDownloadForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_assessment_resource_data_to_spreadsheetforms_data(
            data, public_only=False
        )


class AdminPipelineDownloadForm(AdminModelDownloadForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_pipeline_data_to_spreadsheetforms_data(data, public_only=False)


class AdminModelImportForm(PermissionRequiredMixin, View, ABC):
    """Provides a 1 stage import process.

    This is only suitable for small spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

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
            {
                "data": data,
                "form": form,
            },
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
                missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
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
                    self.__class__._redirect_view,
                    kwargs={"public_id": data.public_id},
                )
            )
        else:
            return render(
                request,
                "indigo/admin/"
                + self.__class__._model.__name__.lower()
                + "/import_form.html",
                {
                    "data": data,
                    "form": form,
                },
            )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


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


class AdminModelImportFormStage1Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 1 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def get(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")

        form = ModelImportStage1Of2Form()

        context = {
            "record": record,
            "form": form,
        }

        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/import_form.html",
            context,
        )

    def post(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")

        form = ModelImportStage1Of2Form(request.POST, request.FILES)

        if form.is_valid():

            # Save the data
            import_data = self._import_model()
            import_data.user = request.user
            self._set_record_on_import_model(record, import_data)
            with open(request.FILES["file"].temporary_file_path(), "rb") as fp:
                import_data.file_data = fp.read()
            import_data.save()

            # Make celery call to start background worker
            self._send_message_to_worker(import_data)

            # redirect to a new URL so user can wait for stage 2 of the process to be ready
            return HttpResponseRedirect(
                reverse(
                    self._redirect_view,
                    kwargs={
                        "public_id": record.public_id,
                        "import_id": import_data.id,
                    },
                )
            )

        else:

            context = {
                "record": record,
                "form": form,
            }

            return render(
                request,
                "indigo/admin/"
                + self.__class__._model.__name__.lower()
                + "/import_form.html",
                context,
            )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectImportFormStage1Of2(AdminModelImportFormStage1Of2):
    _model = Project
    _import_model = ProjectImport
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_import_form_stage_2"

    def _set_record_on_import_model(self, record, import_data):
        import_data.project = Project.objects.get(public_id=record.public_id)

    def _send_message_to_worker(self, import_data):
        task_process_imported_project_file.delay(import_data.id)


class AdminPipelineImportFormStage1Of2(AdminModelImportFormStage1Of2):
    _model = Pipeline
    _import_model = PipelineImport
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_import_form_stage_2"

    def _set_record_on_import_model(self, record, import_data):
        import_data.pipeline = Pipeline.objects.get(public_id=record.public_id)

    def _send_message_to_worker(self, import_data):
        task_process_imported_pipeline_file.delay(import_data.id)


class AdminModelImportFormStage2Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 2 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def _setup(self, request, public_id, import_id):
        try:
            type = Type.objects.get(public_id=self._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
            import_data = self._import_model.objects.get(id=import_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        except self._import_model.DoesNotExist:
            raise Http404("Import does not exist")

        if not self._check_record_and_import_are_linked(record, import_data):
            raise Http404("Import is for another data item")
        if import_data.user != request.user:
            raise Http404("Import is for another user")
        if import_data.imported:
            raise Http404("Import already done")

        if import_data.exception:
            return (
                render(
                    request,
                    "indigo/admin/"
                    + self.__class__._model.__name__.lower()
                    + "/import_form_stage_2_exception.html",
                    {"record": record, "import": import_data},
                ),
                None,
                None,
                None,
            )

        if import_data.file_not_valid:
            return (
                render(
                    request,
                    "indigo/admin/"
                    + self.__class__._model.__name__.lower()
                    + "/import_form_stage_2_file_not_valid.html",
                    {"record": record},
                ),
                None,
                None,
                None,
            )

        if not import_data.data:
            return (
                render(
                    request,
                    "indigo/admin/"
                    + self.__class__._model.__name__.lower()
                    + "/import_form_stage_2_wait.html",
                    {"record": record, "import": import_data},
                ),
                None,
                None,
                None,
            )

        return None, type, record, import_data

    def get(self, request, public_id, import_id):

        view, type, record, import_data = self._setup(request, public_id, import_id)
        if view:
            return view

        # Because a spreadsheet with deleted tabs may have been uploaded,
        # import_data.data isn't the complete data for this record.
        # So merge import data on top of current data and use that to make a data quality report.
        new_event_datas = [
            d
            for d in self._get_edits(record, import_data.data)
            if d.record.type.public_id == self._type_public_id
        ]
        data_quality_report = self._dqr_class(
            new_event_datas[
                0
            ].get_new_data_when_event_applied_to_latest_record_cached_data()
        )
        level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

        form = ModelImportStage2Of2Form()

        context = {
            "record": record,
            "form": form,
            "level_zero_errors": level_zero_errors,
        }

        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/import_form_stage_2.html",
            context,
        )

    def post(self, request, public_id, import_id):

        view, type, record, import_data = self._setup(request, public_id, import_id)
        if view:
            return view

        form = ModelImportStage2Of2Form(request.POST, request.FILES)

        if form.is_valid():

            # Save the event
            new_event_datas = self._get_edits(record, import_data.data)
            newEvent(
                new_event_datas,
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # mark import done
            import_data.imported = Now()
            import_data.save()

            # redirect to project page with message
            messages.add_message(
                request,
                messages.INFO,
                "The data has been imported; remember to moderate it!",
            )
            return HttpResponseRedirect(
                reverse(
                    self._redirect_view,
                    kwargs={"public_id": record.public_id},
                )
            )

        else:
            form = ModelImportStage2Of2Form()

            data_quality_report = self._dqr_class(import_data.data)
            level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

            context = {
                "record": record,
                "form": form,
                "level_zero_errors": level_zero_errors,
            }

            return render(
                request,
                "indigo/admin/"
                + self.__class__._model.__name__.lower()
                + "/import_form_stage_2.html",
                context,
            )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectImportFormStage2Of2(AdminModelImportFormStage2Of2):
    _model = Project
    _import_model = ProjectImport
    _dqr_class = DataQualityReportForProject
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"

    def _check_record_and_import_are_linked(self, record, import_data):
        return record.public_id == import_data.project.public_id

    def _get_edits(self, record, import_json):
        return extract_edits_from_project_spreadsheet(record, import_json)


class AdminPipelineImportFormStage2Of2(AdminModelImportFormStage2Of2):
    _model = Pipeline
    _import_model = PipelineImport
    _dqr_class = DataQualityReportForPipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"

    def _check_record_and_import_are_linked(self, record, import_data):
        return record.public_id == import_data.pipeline.public_id

    def _get_edits(self, record, import_json):
        return extract_edits_from_pipeline_spreadsheet(record, import_json)


class AdminModelChangeStatus(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        record = data.record

        form = RecordChangeStatusForm()

        context = {
            "record": record,
            "form": form,
        }

        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/change_status.html",
            context,
        )

    def post(self, request, public_id):

        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        record = data.record

        # Create a form instance and populate it with data from the request (binding):
        form = RecordChangeStatusForm(request.POST)

        # For some users, not all combinations of actions are valid.
        if not request.user.has_perm("indigo.admin"):
            if form.data["status"] == "PUBLIC" and form.data["when"] == "immediate":
                form.add_error(
                    None,
                    ValidationError(
                        "With this access level, you can not make something public without submitting if for moderation."
                    ),
                )

        # Check if the form is valid:
        if form.is_valid():
            approved = form.cleaned_data["when"] == "immediate"

            # Save the event
            new_event_data = NewEventData(
                type,
                record,
                {"status": form.cleaned_data["status"]},
                mode=jsondataferret.EVENT_MODE_MERGE,
                approved=approved,
            )
            newEvent(
                [new_event_data],
                user=request.user,
                comment=form.cleaned_data["comment"],
            )

            # redirect to a new URL:
            messages.add_message(
                request,
                messages.INFO,
                "Change made!" if approved else "Change sent for moderation.",
            )
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": record.public_id},
                )
            )

        context = {
            "record": record,
            "form": form,
        }

        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/change_status.html",
            context,
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectChangeStatus(AdminModelChangeStatus):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"


class AdminOrganisationChangeStatus(AdminModelChangeStatus):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _redirect_view = "indigo_admin_organisation_index"


class AdminFundChangeStatus(AdminModelChangeStatus):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _redirect_view = "indigo_admin_fund_index"


class AdminPipelineChangeStatus(AdminModelChangeStatus):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"


class AdminAssessmentResourceChangeStatus(AdminModelChangeStatus):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _redirect_view = "indigo_admin_assessment_resource_index"


class AdminJoiningUpInitiativeChangeStatus(AdminModelChangeStatus):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _redirect_view = "indigo_admin_joining_up_initiative_index"


class AdminModelNew(PermissionRequiredMixin, View, ABC):
    def get(self, request):
        form = self.__class__._form_class()
        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/new.html",
            {
                "form": form,
            },
        )

    @method_decorator(transaction.atomic)
    def post(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        form = self.__class__._form_class(request.POST)
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

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": id},
                )
            )

        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/new.html",
            {
                "form": form,
            },
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


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


class AdminPipelineNew(AdminModelNew):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _form_class = PipelineNewForm
    _redirect_view = "indigo_admin_pipeline_index"


class AdminModelJSONFormNew(PermissionRequiredMixin, View, ABC):
    def get_template(self):
        return f"indigo/admin/{self.__class__._model.__name__.lower()}/new.html"

    def get(self, request):
        return render(
            request, self.get_template(), {"form": self.__class__._form_class()}
        )

    @method_decorator(transaction.atomic)
    def post(self, request):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        form = self.__class__._form_class(request.POST)
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # Save the event
            id = indigo.utils.get_next_record_id(type)

            data = NewEventData(
                type,
                id,
                form.cleaned_data["data"],
            )
            newEvent([data], user=request.user, comment=form.cleaned_data["comment"])

            # redirect to page with message
            messages.add_message(
                request,
                messages.INFO,
                "New record submitted. The data will not be available until it's been moderated.",
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": id},
                )
            )

        return render(request, self.get_template(), {"form": form})

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminJoiningUpInitiativeNew(AdminModelJSONFormNew):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeNewForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"


class AdminModelEdit(PermissionRequiredMixin, View, ABC):
    def get_template(self):
        return f"indigo/admin/{self.__class__._model.__name__.lower()}/edit.html"

    def get(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            instance = Model.objects.get(public_id=public_id)
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")

        form = Form(initial={"data": instance.data_private})
        return render(
            request, self.get_template(), {"form": form, "instance": instance}
        )

    @method_decorator(transaction.atomic)
    def post(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
            instance = Model.objects.get(public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")

        form = Form(request.POST, request.FILES)

        if form.is_valid():
            data = form.cleaned_data["data"]

            new_event_datas = extract_edits_from_joining_up_initiative_form(
                record, data
            )

            newEvent(
                new_event_datas, user=request.user, comment=form.cleaned_data["comment"]
            )

            # redirect to page with message
            messages.add_message(
                request,
                messages.INFO,
                "Updates submitted. The changes will not be available until the updates have been moderated.",
            )

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": public_id},
                )
            )

        return render(
            request, self.get_template(), {"form": form, "instance": instance}
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminJoiningUpInitiativeEdit(AdminModelEdit):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeEditForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"


class AdminModelModerate(PermissionRequiredMixin, View, ABC):
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

        if request.method == "POST" and request.user.has_perm("indigo.admin"):

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

        return render(
            request,
            "indigo/admin/" + self.__class__._model.__name__.lower() + "/moderate.html",
            {"type": type, "record": record, "edits": edits},
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundModerate(AdminModelModerate):
    _model = Fund
    _redirect_view = "indigo_admin_fund_index"


class AdminAssessmentResourceModerate(AdminModelModerate):
    _model = AssessmentResource
    _redirect_view = "indigo_admin_assessment_resource_index"


class AdminPipelineModerate(AdminModelModerate):
    _model = Pipeline
    _redirect_view = "indigo_admin_pipeline_index"


class AdminJoiningUpInitiativeModerate(AdminModelModerate):
    _model = JoiningUpInitiative
    _redirect_view = "indigo_admin_joining_up_initiative_index"


class AdminModelHistory(PermissionRequiredMixin, View, ABC):
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

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundHistory(AdminModelHistory):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID


class AdminAssessmentResourceHistory(AdminModelHistory):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class AdminPipelineHistory(AdminModelHistory):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID


class AdminJoiningUpInitiativeHistory(AdminModelHistory):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID


class AdminModelDataQualityReport(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")

        dqr = self.__class__._data_quality_report(record.cached_data)

        return render(
            request,
            "indigo/admin/"
            + self.__class__._model.__name__.lower()
            + "/data_quality_report.html",
            {
                "type": type,
                "record": record,
                "errors_by_priority_level": dqr.get_errors_in_priority_levels(),
                "data_quality_report": dqr,
            },
        )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDataQualityReport(AdminModelDataQualityReport):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _data_quality_report = DataQualityReportForProject


class AdminPipelineDataQualityReport(AdminModelDataQualityReport):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _data_quality_report = DataQualityReportForPipeline


########################### Admin - sandboxes


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


########################### Admin - Event


@permission_admin_or_data_steward_required()
def admin_event_index(request, event_id):
    try:
        event = Event.objects.get(public_id=event_id)
    except Event.DoesNotExist:
        raise Http404("Event does not exist")
    edits_created = event.edits_created.all()
    edits_approved = event.edits_approved.all()
    edits_refused = event.edits_refused.all()
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
    return render(
        request,
        "indigo/admin/edit/index.html",
        {
            "edit": edit,
        },
    )


########################### Admin - Moderate


@permission_admin_or_data_steward_required()
def admin_to_moderate(request):
    try:
        type_project = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        type_organisation = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        type_fund = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        type_pipeline = Type.objects.get(public_id=TYPE_PIPELINE_PUBLIC_ID)
        type_assessment_resource = Type.objects.get(
            public_id=TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
        )
        type_joining_up_initiative = Type.objects.get(
            public_id=TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
        )
    except Type.DoesNotExist:
        raise Http404("Type does not exist")
    return render(
        request,
        "indigo/admin/to_moderate.html",
        {
            "projects": Record.objects.filter_needs_moderation_by_type(type_project),
            "organisations": Record.objects.filter_needs_moderation_by_type(
                type_organisation
            ),
            "funds": Record.objects.filter_needs_moderation_by_type(type_fund),
            "pipelines": Record.objects.filter_needs_moderation_by_type(type_pipeline),
            "assessment_resources": Record.objects.filter_needs_moderation_by_type(
                type_assessment_resource
            ),
            "joining_up_initiatives": Record.objects.filter_needs_moderation_by_type(
                type_joining_up_initiative
            ),
        },
    )
