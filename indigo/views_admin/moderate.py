"""Approving or rejecting the edits waiting on a record."""
from abc import ABC

import jsondataferret
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from jsondataferret.models import Edit, Record, Type

from indigo.models import AssessmentResource, Fund, JoiningUpInitiative, Pipeline
from indigo.views_admin.common import (
    _add_moderation_message,
    _edit_changes,
    _subpage_context,
)


class AdminModelModerate(PermissionRequiredMixin, View, ABC):
    def get(self, request, public_id):
        return self.post(request, public_id)

    def post(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._model.type_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        edits = Edit.objects.filter(
            record=record, approval_event=None, refusal_event=None
        )

        if request.method == "POST" and request.user.has_perm("indigo.admin"):

            # TODO check CSFR

            actions = []
            for edit in edits:
                action = request.POST.get("action_" + str(edit.id))
                if action == "approve":
                    actions.append(
                        jsondataferret.pythonapi.newevent.NewEventApproval(edit)
                    )
                elif action == "reject":
                    actions.append(
                        jsondataferret.pythonapi.newevent.NewEventRejection(edit)
                    )

            if actions:
                jsondataferret.pythonapi.newevent.newEvent(
                    actions, user=request.user, comment=request.POST.get("comment")
                )
                _add_moderation_message(request, actions)
                return HttpResponseRedirect(
                    reverse(
                        self.__class__._redirect_view,
                        kwargs={"public_id": record.public_id},
                    )
                )

        for edit in edits:
            edit.changes = _edit_changes(edit, record)

        return render(
            request,
            "indigo/admin/moderate.html",
            _subpage_context(record, edits=edits),
        )


class AdminFundModerate(AdminModelModerate):
    _model = Fund
    _redirect_view = "indigo_admin_fund_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceModerate(AdminModelModerate):
    _model = AssessmentResource
    _redirect_view = "indigo_admin_assessment_resource_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineModerate(AdminModelModerate):
    _model = Pipeline
    _redirect_view = "indigo_admin_pipeline_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeModerate(AdminModelModerate):
    _model = JoiningUpInitiative
    _redirect_view = "indigo_admin_joining_up_initiative_index"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
