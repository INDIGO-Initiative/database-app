"""Admin views for organisations that have no class-based equivalent."""
import csv
import os
import random
import tempfile

import jsondataferret
import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from jsondataferret.models import Edit, Record, Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.utils
from indigo import TYPE_ORGANISATION_PUBLIC_ID
from indigo.forms import OrganisationImportForm, OrganisationNewForm
from indigo.listpages import list_context
from indigo.models import Organisation
from indigo.spreadsheetforms import (
    convert_organisation_data_to_spreadsheetforms_data,
    extract_edits_from_organisation_spreadsheet,
)
from indigo.views_admin.common import (
    DOWNLOAD_FORM_NOTE,
    _add_moderation_message,
    _admin_record_page,
    _edit_changes,
    _new_page,
    _record_history_page,
    _related_records_page,
    _subpage_context,
    permission_admin_or_data_steward_required,
)


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
        "indigo/admin/list.html",
        list_context(
            request,
            organisations,
            title="Organisations",
            noun_plural="organisations",
            name_field="data_private",
            index_url_name="indigo_admin_organisation_index",
            list_url_name="indigo_admin_organisation_list",
            items_key="organisations",
            search_term=search_term,
            searchable=True,
            search_placeholder="Name or ID",
            edit_url_name="indigo_admin_organisation_edit",
            add_url_name="indigo_admin_organisation_new",
            add_label="Organisation",
            menu_groups=[
                {
                    "heading": "Spreadsheets",
                    "items": [
                        {
                            "label": "Download Blank Form",
                            "url_name": "indigo_admin_organisation_download_blank_form",
                        },
                        {
                            "label": "Download all as CSV",
                            "url_name": "indigo_admin_organisation_download_all_csv",
                        },
                    ],
                }
            ],
            search_extra_template="indigo/admin/includes/organisation_goto.html",
        ),
    )


@permission_admin_or_data_steward_required()
def admin_organisations_search_json(request):
    """Used by the organisation picker on the edit forms. Either search by name, or look up by a comma separated list of IDs."""
    organisations = Organisation.objects.all()
    ids = [i.strip() for i in request.GET.get("ids", "").split(",") if i.strip()]
    search_term = request.GET.get("search", "").strip()
    if ids:
        organisations = organisations.filter(public_id__in=ids)
    elif search_term:
        organisations = organisations.filter(
            full_text_search_private__search=search_term
        )
    else:
        organisations = organisations.none()
    organisations = organisations.order_by("public_id")[:20]
    return JsonResponse(
        {
            "results": [
                {
                    "id": organisation.public_id,
                    "name": organisation.data_private.get("name", {}).get("value", ""),
                }
                for organisation in organisations
            ]
        }
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
    return _admin_record_page(
        request,
        organisation,
        record_title="Organisation",
        type_public_id=TYPE_ORGANISATION_PUBLIC_ID,
        url_prefix="organisation",
        list_title="Organisations",
        extra_actions=[
            ("Projects Using This", "indigo_admin_organisation_projects", True),
            ("Pipelines Using This", "indigo_admin_organisation_pipelines", True),
        ],
        spreadsheets=[
            ("Download Form", "indigo_admin_organisation_download_form"),
            ("Upload/Import Form", "indigo_admin_organisation_import_form"),
        ],
        notes=[DOWNLOAD_FORM_NOTE],
    )


@permission_required("indigo.admin")
def admin_organisation_projects(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return _related_records_page(
        request,
        organisation,
        "Projects",
        "project",
        [
            link.project
            for link in organisation.included_by_projects.all()
            if link.in_current_data
        ],
    )


@permission_required("indigo.admin")
def admin_organisation_pipelines(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    return _related_records_page(
        request,
        organisation,
        "Pipelines",
        "pipeline",
        [
            link.pipeline
            for link in organisation.included_by_pipelines.all()
            if link.in_current_data
        ],
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

    return render(
        request, "indigo/admin/import_form.html", _subpage_context(data, form=form)
    )


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

            messages.add_message(
                request,
                messages.INFO,
                "Created. Now fill in the rest of the details; they will be available once they have been moderated.",
            )

            # redirect to the edit form
            return HttpResponseRedirect(
                reverse(
                    "indigo_admin_organisation_edit",
                    kwargs={"public_id": id},
                )
            )

    # If this is a GET (or any other method) create the default form.
    else:
        form = OrganisationNewForm()

    return _new_page(request, TYPE_ORGANISATION_PUBLIC_ID, form)


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
            _add_moderation_message(request, actions)

        return HttpResponseRedirect(
            reverse(
                "indigo_admin_organisation_index",
                kwargs={"public_id": public_id},
            )
        )

    for edit in edits:
        # TODO This will not take account of data_key on an edit If we start using that we will need to check this
        edit.changes = _edit_changes(edit, record)

    return render(
        request,
        "indigo/admin/moderate.html",
        _subpage_context(record, edits=edits),
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

    return _record_history_page(request, record)
