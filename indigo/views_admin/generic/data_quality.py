"""The base of the data quality report of one record."""
from abc import ABC

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.views import View

from indigo.views_admin.common import subpage_context


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
            subpage_context(
                record,
                errors_by_priority_level=dqr.get_errors_in_priority_levels(),
                data_quality_report=dqr,
            ),
        )

    def has_permission_with_data(self, data):
        return True
