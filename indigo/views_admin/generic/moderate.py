"""The base of the page for approving or rejecting the edits waiting on a record."""
import jsondataferret
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from jsondataferret.models import Edit, Record, Type

from indigo.views_admin.common import (
    AdminModelRecordView,
    add_moderation_message,
    edit_changes,
    subpage_context,
)


class AdminModelModerate(AdminModelRecordView):
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
        self._check_access(public_id)
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
                add_moderation_message(request, actions)
                return HttpResponseRedirect(
                    reverse(
                        self.__class__._redirect_view,
                        kwargs={"public_id": record.public_id},
                    )
                )

        for edit in edits:
            edit.changes = edit_changes(edit, record)

        return render(
            request,
            "indigo/admin/moderate.html",
            subpage_context(record, edits=edits),
        )
