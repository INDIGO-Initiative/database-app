"""The bases of importing a spreadsheet form into a record (one stage, or the two stages used for large forms)."""
from abc import ABC

import spreadsheetforms.api
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Now
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from jsondataferret.pythonapi.newevent import newEvent

from indigo.forms import ModelImportStage1Of2Form, ModelImportStage2Of2Form
from indigo.views_admin.common import subpage_context


def read_spreadsheet(guide_spec, file_path):
    return spreadsheetforms.api.get_data_from_form_with_guide_spec(
        guide_spec,
        file_path,
        date_format=getattr(
            settings, "JSONDATAFERRET_SPREADSHEET_FORM_DATE_FORMAT", None
        ),
        missing_worksheet_action=spreadsheetforms.api.GetDataFromFormMissingWorksheetAction.SET_NO_DATA,
    )


class AdminModelImportForm(PermissionRequiredMixin, View, ABC):
    """Provides a 1 stage import process.

    This is only suitable for small spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def _get_import_json(self, file_path):
        """The data in the uploaded spreadsheet. A type can override this to choose how to read it."""
        return read_spreadsheet(
            settings.JSONDATAFERRET_TYPE_INFORMATION[self.__class__._model.type_id][
                "spreadsheet_form_guide_spec"
            ],
            file_path,
        )

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        return render(
            request,
            "indigo/admin/import_form.html",
            subpage_context(data.record, form=self.__class__._form_class()),
        )

    def post(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        form = self.__class__._form_class(request.POST, request.FILES)
        if form.is_valid():
            # get data
            import_json = self._get_import_json(
                request.FILES["file"].temporary_file_path()
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
                "indigo/admin/import_form.html",
                subpage_context(data.record, form=form),
            )


class AdminModelImportFormStage1Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 1 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        form = ModelImportStage1Of2Form()

        return render(
            request,
            "indigo/admin/import_form.html",
            subpage_context(record, form=form),
        )

    def post(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

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

            return render(
                request,
                "indigo/admin/import_form.html",
                subpage_context(record, form=form),
            )

    def has_permission_with_data(self, data):
        return True


class AdminModelImportFormStage2Of2(PermissionRequiredMixin, View, ABC):
    """Provides part 2 of a 2 stage import process.

    This must be used for large spreadsheet forms; otherwise it takes to long to load the data from the Excel file and Heroku will time out."""

    def _setup(self, request, public_id, import_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record
        type = record.type

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        try:
            import_data = self._import_model.objects.get(id=import_id)
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
                    "indigo/admin/import_message.html",
                    subpage_context(
                        record,
                        message="There was a problem. Please contact support.",
                    ),
                ),
                None,
                None,
                None,
            )

        if import_data.file_not_valid:
            return (
                render(
                    request,
                    "indigo/admin/import_message.html",
                    subpage_context(
                        record,
                        message="That does not seem to be a "
                        + record.type.public_id
                        + " spreadsheet, so it can not be imported.",
                    ),
                ),
                None,
                None,
                None,
            )

        if not import_data.data:
            return (
                render(
                    request,
                    "indigo/admin/import_message.html",
                    subpage_context(
                        record,
                        message="We are processing your file, please wait ...",
                        refresh_url=reverse(
                            f"indigo_admin_{record.type.public_id}_import_form_stage_2",
                            kwargs={
                                "public_id": record.public_id,
                                "import_id": import_data.id,
                            },
                        ),
                    ),
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

        return render(
            request,
            "indigo/admin/import_stage_2.html",
            subpage_context(record, form=form, level_zero_errors=level_zero_errors),
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
            data_quality_report = self._dqr_class(import_data.data)
            level_zero_errors = data_quality_report.get_errors_for_priority_level(0)

            return render(
                request,
                "indigo/admin/import_stage_2.html",
                subpage_context(record, form=form, level_zero_errors=level_zero_errors),
            )

    def has_permission_with_data(self, data):
        return True
