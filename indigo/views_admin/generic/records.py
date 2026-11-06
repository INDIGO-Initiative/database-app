"""The base of the admin page of one record of a type."""
from django.http import Http404

from indigo.views_admin.common import AdminModelRecordView, admin_record_page


class AdminModelIndex(AdminModelRecordView):
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
        self._check_access(public_id)
        return admin_record_page(
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
