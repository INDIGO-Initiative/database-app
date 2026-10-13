"""Adding a record."""
from abc import ABC

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from jsondataferret.models import Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

import indigo.utils
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
)
from indigo.forms import (
    AssessmentResourceNewForm,
    FundNewForm,
    JoiningUpInitiativeNewForm,
    PipelineNewForm,
)
from indigo.models import AssessmentResource, Fund, JoiningUpInitiative, Pipeline
from indigo.views_admin.common import _new_page


class AdminModelNew(PermissionRequiredMixin, View, ABC):
    def get(self, request):
        form = self.__class__._form_class()
        return _new_page(request, self.__class__._type_public_id, form)

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

            messages.add_message(
                request,
                messages.INFO,
                "Created. Now fill in the rest of the details; they will be available once they have been moderated.",
            )

            # redirect to the edit form
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": id},
                )
            )

        return _new_page(request, self.__class__._type_public_id, form)


class AdminFundNew(AdminModelNew):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _form_class = FundNewForm
    _redirect_view = "indigo_admin_fund_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceNew(AdminModelNew):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _form_class = AssessmentResourceNewForm
    _redirect_view = "indigo_admin_assessment_resource_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineNew(AdminModelNew):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _form_class = PipelineNewForm
    _redirect_view = "indigo_admin_pipeline_edit"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminModelJSONFormNew(PermissionRequiredMixin, View, ABC):
    def _page(self, request, form):
        return _new_page(request, self.__class__._type_public_id, form, full_form=True)

    def get(self, request):
        return self._page(request, self.__class__._form_class())

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

        return self._page(request, form)


class AdminJoiningUpInitiativeNew(AdminModelJSONFormNew):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _form_class = JoiningUpInitiativeNewForm
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
