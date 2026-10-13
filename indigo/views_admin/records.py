"""The admin page of one record of each type, and lists of records linked to it."""
from abc import ABC

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404
from django.views import View

from indigo.models import AssessmentResource, Fund, JoiningUpInitiative, Pipeline
from indigo.views_admin.common import (
    DOWNLOAD_FORM_NOTE,
    _admin_record_page,
    _related_records_page,
)
from indigo.views_admin.downloads import _form_downloads


class AdminModelIndex(PermissionRequiredMixin, View, ABC):
    """The admin page of one record of a type. Each says (in its class variables):

    _record_title / _list_title / _url_prefix: the words to use, and the start of its view names
    _extra_actions: (label, url name, admin only?) for pages this type has of its own
    _spreadsheets / _notes: what goes in the Spreadsheets part of the More menu, if there is one"""

    _extra_actions = ()
    _spreadsheets = ()
    _notes = ()

    def get(self, request, public_id):
        cls = self.__class__
        try:
            data = cls._model.objects.get(public_id=public_id)
        except cls._model.DoesNotExist:
            raise Http404("Data does not exist")
        return _admin_record_page(
            request,
            data,
            record_title=cls._record_title,
            type_public_id=cls._model.type_id,
            url_prefix=cls._url_prefix,
            list_title=cls._list_title,
            extra_actions=cls._extra_actions,
            spreadsheets=cls._spreadsheets,
            notes=cls._notes,
        )


class AdminFundIndex(AdminModelIndex):
    _model = Fund
    _record_title = "Fund"
    _list_title = "Funds"
    _url_prefix = "fund"
    _extra_actions = [("Projects Using This", "indigo_admin_fund_projects", True)]
    _spreadsheets = _form_downloads("fund")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceIndex(AdminModelIndex):
    _model = AssessmentResource
    _record_title = "Assessment Resource"
    _list_title = "Assessment Resources"
    _url_prefix = "assessment_resource"
    _spreadsheets = _form_downloads("assessment_resource")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineIndex(AdminModelIndex):
    _model = Pipeline
    _record_title = "Pipeline"
    _list_title = "Pipelines"
    _url_prefix = "pipeline"
    _extra_actions = [
        ("Data Quality Report", "indigo_admin_pipeline_data_quality_report")
    ]
    _spreadsheets = _form_downloads("pipeline")
    _notes = [DOWNLOAD_FORM_NOTE]

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeIndex(AdminModelIndex):
    _model = JoiningUpInitiative
    _record_title = "Joining Up Initiative"
    _list_title = "Joining Up Initiatives"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


@permission_required("indigo.admin")
def admin_fund_projects(request, public_id):
    try:
        fund = Fund.objects.get(public_id=public_id)
    except Fund.DoesNotExist:
        raise Http404("Fund does not exist")
    return _related_records_page(
        request,
        fund,
        "Projects",
        "project",
        [
            link.project
            for link in fund.included_by_projects.all()
            if link.in_current_data
        ],
    )
