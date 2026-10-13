"""Downloading blank and filled-in spreadsheet forms."""
import os
import random
import tempfile
from abc import ABC

import spreadsheetforms.api
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.views import View

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import AssessmentResource, Fund, Pipeline, Project
from indigo.spreadsheetforms import (
    convert_assessment_resource_data_to_spreadsheetforms_data,
    convert_fund_data_to_spreadsheetforms_data,
    convert_pipeline_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
)
from indigo.views_admin.common import user_can_access_project


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


class AdminProjectDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminProjectDownloadBlankSimpleForm(AdminModelDownloadBlankForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineDownloadBlankForm(AdminModelDownloadBlankForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


def _blank_form_menu(url_name):
    return [
        {
            "heading": "Spreadsheets",
            "items": [{"label": "Download Blank Form", "url_name": url_name}],
        }
    ]


def _form_downloads(prefix):
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


class AdminProjectDownloadForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminProjectDownloadSimpleForm(AdminModelDownloadForm):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PROJECT_PUBLIC_ID
    ).get("simple_spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_project_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminFundDownloadForm(AdminModelDownloadForm):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_FUND_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_fund_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


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

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineDownloadForm(AdminModelDownloadForm):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _guide_file_name = settings.JSONDATAFERRET_TYPE_INFORMATION.get(
        TYPE_PIPELINE_PUBLIC_ID
    ).get("spreadsheet_form_guide")

    def _get_data_for_form(self, data):
        return convert_pipeline_data_to_spreadsheetforms_data(data, public_only=False)

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
