"""The bases of the pages for adding a record."""
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
from indigo.views_admin.common import new_page


class AdminModelNew(PermissionRequiredMixin, View, ABC):
    def _after_create(self, request, public_id):
        """Anything else to do once the record has been created (by default, nothing)."""

    def get(self, request):
        form = self.__class__._form_class()
        return new_page(request, self.__class__._type_public_id, form)

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
            self._after_create(request, id)

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

        return new_page(request, self.__class__._type_public_id, form)


class AdminModelJSONFormNew(PermissionRequiredMixin, View, ABC):
    def _page(self, request, form):
        return new_page(request, self.__class__._type_public_id, form, full_form=True)

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
