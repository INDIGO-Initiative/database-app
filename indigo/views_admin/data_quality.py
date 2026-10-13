"""Data quality reports."""
from abc import ABC

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.views import View

from indigo import TYPE_PIPELINE_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.dataqualityreport import (
    DataQualityReportForAllProjects,
    DataQualityReportForPipeline,
    DataQualityReportForProject,
)
from indigo.models import Pipeline, Project
from indigo.views_admin.common import _subpage_context, user_can_access_project


@permission_required("indigo.admin")
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


@permission_required("indigo.admin")
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


@permission_required("indigo.admin")
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


class AdminModelDataQualityReport(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        record = data.record

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        dqr = self.__class__._data_quality_report(record.cached_data)

        return render(
            request,
            "indigo/admin/data_quality_report.html",
            _subpage_context(
                record,
                errors_by_priority_level=dqr.get_errors_in_priority_levels(),
                data_quality_report=dqr,
            ),
        )

    def has_permission_with_data(self, data):
        return True


class AdminProjectDataQualityReport(AdminModelDataQualityReport):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _data_quality_report = DataQualityReportForProject

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminPipelineDataQualityReport(AdminModelDataQualityReport):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _data_quality_report = DataQualityReportForPipeline

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
