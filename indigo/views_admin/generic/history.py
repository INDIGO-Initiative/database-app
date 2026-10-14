"""The base of the History page of one record."""
from django.http import Http404
from jsondataferret.models import Record, Type

from indigo.views_admin.common import AdminModelRecordView, record_history_page


class AdminModelHistory(AdminModelRecordView):
    def get(self, request, public_id):
        try:
            type = Type.objects.get(public_id=self.__class__._type_public_id)
            record = Record.objects.get(type=type, public_id=public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        except Record.DoesNotExist:
            raise Http404("Record does not exist")
        self._check_access(public_id)
        return record_history_page(request, record)
