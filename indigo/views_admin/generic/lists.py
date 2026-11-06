"""The base of the admin list page of a type of record."""
from abc import ABC

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View
from jsondataferret.models import Record, Type

from indigo.listpages import list_context, search_filter


class AdminModelList(PermissionRequiredMixin, View, ABC):
    """A list of records of one type. Each list says (in its class variables):

    _list_title / _noun_plural / _add_label: the words to use
    _url_prefix: the start of its view names, eg "fund" for indigo_admin_fund_index
    _search_keys: the keys of the data whose value can be searched, as well as the ID
    _menu_groups: what goes in the More menu (see indigo.listpages.visible_menu)

    A type that lists differently can set _name_field (the JSON field with the name; default cached_data),
    _searchable, _search_placeholder and _search_extra_template, and override _get_items."""

    _search_keys = []
    _menu_groups = []
    _name_field = "cached_data"
    _searchable = False
    _search_placeholder = None
    _search_extra_template = None

    def _get_items(self, request, search_term):
        """The records to list, matching the search. By default every record of the type, searched by ID and the
        _search_keys; a type can override this to list differently."""
        cls = self.__class__
        try:
            type = Type.objects.get(public_id=cls._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        datas = Record.objects.filter(type=type).order_by("public_id")
        if search_term and cls._search_keys:
            datas = datas.filter(
                search_filter(search_term, "cached_data", cls._search_keys)
            )
        return datas

    def get(self, request):
        cls = self.__class__
        search_term = request.GET.get("search", "").strip()
        datas = self._get_items(request, search_term)
        return render(
            request,
            "indigo/admin/list.html",
            list_context(
                request,
                datas,
                title=cls._list_title,
                noun_plural=cls._noun_plural,
                name_field=cls._name_field,
                index_url_name=f"indigo_admin_{cls._url_prefix}_index",
                list_url_name=f"indigo_admin_{cls._url_prefix}_list",
                search_term=search_term,
                searchable=cls._searchable or bool(cls._search_keys),
                search_placeholder=cls._search_placeholder
                or f"{cls._add_label} ID or name",
                edit_url_name=f"indigo_admin_{cls._url_prefix}_edit",
                add_url_name=f"indigo_admin_{cls._url_prefix}_new",
                add_label=cls._add_label,
                menu_groups=cls._menu_groups,
                search_extra_template=cls._search_extra_template,
            ),
        )
