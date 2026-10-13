"""Changing the status of a record."""
from abc import ABC

import jsondataferret
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.forms import RecordChangeStatusForm
from indigo.models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    Project,
)
from indigo.views_admin.common import _subpage_context, user_can_access_project


class AdminModelChangeStatus(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

        record = data.record

        form = RecordChangeStatusForm()

        return render(
            request,
            "indigo/admin/change_status.html",
            _subpage_context(record, form=form),
        )

    def post(self, request, public_id):

        try:
            data = self.__class__._model.objects.get(public_id=public_id)
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")

        if not self.has_permission_with_data(data):
            raise PermissionDenied("You can not see data")

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
                record.type,
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

        return render(
            request,
            "indigo/admin/change_status.html",
            _subpage_context(record, form=form),
        )

    def has_permission_with_data(self, data):
        return True


class AdminProjectChangeStatus(AdminModelChangeStatus):
    _model = Project
    _type_public_id = TYPE_PROJECT_PUBLIC_ID
    _redirect_view = "indigo_admin_project_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")

    def has_permission_with_data(self, data):
        return user_can_access_project(self.request.user, data)


class AdminOrganisationChangeStatus(AdminModelChangeStatus):
    _model = Organisation
    _type_public_id = TYPE_ORGANISATION_PUBLIC_ID
    _redirect_view = "indigo_admin_organisation_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminFundChangeStatus(AdminModelChangeStatus):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminPipelineChangeStatus(AdminModelChangeStatus):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminAssessmentResourceChangeStatus(AdminModelChangeStatus):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeChangeStatus(AdminModelChangeStatus):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
