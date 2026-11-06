"""The base of the page for editing a record with the web form."""
from abc import ABC

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from jsondataferret.models import Record, Type
from jsondataferret.pythonapi.newevent import newEvent

from indigo.spreadsheetforms import extract_edits_from_form
from indigo.views_admin.common import add_schema_warnings_message


class AdminModelEdit(PermissionRequiredMixin, View, ABC):
    """The page for editing a record. Each says (in its class variables) _record_title and _list_title, and
    _redirect_view, the record's own page, which also names the rest of its views."""

    def get_template(self):
        return "indigo/admin/edit.html"

    def _context(self, form, instance):
        cls = self.__class__
        name = (instance.data_private or {}).get("name")
        return {
            "form": form,
            "instance": instance,
            "record_title": cls._record_title,
            "list_title": cls._list_title,
            "list_url": reverse(cls._redirect_view.removesuffix("_index") + "_list"),
            "record_url": reverse(
                cls._redirect_view, kwargs={"public_id": instance.public_id}
            ),
            "display_name": name.get("value", "") if isinstance(name, dict) else "",
        }

    def has_permission_with_data(self, data):
        return True

    def _get_edits(self, record, data):
        return extract_edits_from_form(self._type_public_id, record, data)

    def get(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            instance = Model.objects.get(public_id=public_id)
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")
        if not self.has_permission_with_data(instance):
            raise PermissionDenied("You can not see data")

        form = Form(initial={"data": instance.data_private})
        return render(request, self.get_template(), self._context(form, instance))

    @method_decorator(transaction.atomic)
    def post(self, request, public_id):
        Model = self.__class__._model
        Form = self.__class__._form_class
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
            instance = Model.objects.get(public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        except Model.DoesNotExist:
            raise Http404(f"{Model.__name__} does not exist")
        if not self.has_permission_with_data(instance):
            raise PermissionDenied("You can not see data")

        form = Form(request.POST, request.FILES)

        if form.is_valid():
            data = form.cleaned_data["data"]

            new_event_datas = self._get_edits(record, data)

            newEvent(
                new_event_datas, user=request.user, comment=form.cleaned_data["comment"]
            )

            # redirect to page with message
            messages.add_message(
                request,
                messages.INFO,
                "Updates submitted. The changes will not be available until the updates have been moderated.",
            )
            add_schema_warnings_message(request, form)

            # redirect to a new URL:
            return HttpResponseRedirect(
                reverse(
                    self.__class__._redirect_view,
                    kwargs={"public_id": public_id},
                )
            )

        return render(request, self.get_template(), self._context(form, instance))
