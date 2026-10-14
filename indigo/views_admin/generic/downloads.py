"""The bases of downloading blank and filled-in spreadsheet forms."""
import os
import random
import tempfile
from abc import ABC

import spreadsheetforms.api
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.views import View


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


def blank_form_menu(url_name):
    return [
        {
            "heading": "Spreadsheets",
            "items": [{"label": "Download Blank Form", "url_name": url_name}],
        }
    ]


def form_downloads(prefix):
    return [
        ("Download Form", f"indigo_admin_{prefix}_download_form"),
        ("Upload/Import Form", f"indigo_admin_{prefix}_import_form"),
    ]


class AdminModelDownloadForm(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

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

    def has_permission_with_data(self, data):
        return True
