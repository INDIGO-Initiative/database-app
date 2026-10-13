"""The admin list page of each type of record."""
from abc import ABC

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View
from jsondataferret.models import Record, Type

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
)
from indigo.listpages import list_context, search_filter
from indigo.models import AssessmentResource, Fund, JoiningUpInitiative, Pipeline
from indigo.views_admin.downloads import _blank_form_menu


class AdminModelList(PermissionRequiredMixin, View, ABC):
    """A list of records of one type. Each list says (in its class variables):

    _list_title / _noun_plural / _add_label: the words to use
    _url_prefix: the start of its view names, eg "fund" for indigo_admin_fund_index
    _search_keys: the keys of the data whose value can be searched, as well as the ID
    _menu_groups: what goes in the More menu (see indigo.listpages.visible_menu)"""

    _search_keys = []
    _menu_groups = []

    def get(self, request):
        cls = self.__class__
        try:
            type = Type.objects.get(public_id=cls._type_public_id)
        except Type.DoesNotExist:
            raise Http404("Type does not exist")
        datas = Record.objects.filter(type=type).order_by("public_id")
        search_term = request.GET.get("search", "").strip()
        if search_term and cls._search_keys:
            datas = datas.filter(
                search_filter(search_term, "cached_data", cls._search_keys)
            )
        return render(
            request,
            "indigo/admin/list.html",
            list_context(
                request,
                datas,
                title=cls._list_title,
                noun_plural=cls._noun_plural,
                name_field="cached_data",
                index_url_name=f"indigo_admin_{cls._url_prefix}_index",
                list_url_name=f"indigo_admin_{cls._url_prefix}_list",
                items_key="datas",
                search_term=search_term,
                searchable=bool(cls._search_keys),
                search_placeholder=f"{cls._add_label} ID or name",
                edit_url_name=f"indigo_admin_{cls._url_prefix}_edit",
                add_url_name=f"indigo_admin_{cls._url_prefix}_new",
                add_label=cls._add_label,
                menu_groups=cls._menu_groups,
            ),
        )


class AdminFundList(AdminModelList):
    _model = Fund
    _type_public_id = TYPE_FUND_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Funds"
    _noun_plural = "funds"
    _add_label = "Fund"
    _url_prefix = "fund"
    _menu_groups = _blank_form_menu("indigo_admin_fund_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin") or user.has_perm("indigo.data_steward")


class AdminAssessmentResourceList(AdminModelList):
    _model = AssessmentResource
    _type_public_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Assessment Resources"
    _noun_plural = "assessment resources"
    _add_label = "Assessment Resource"
    _url_prefix = "assessment_resource"
    _menu_groups = _blank_form_menu(
        "indigo_admin_assessment_resource_download_blank_form"
    )

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminPipelineList(AdminModelList):
    _model = Pipeline
    _type_public_id = TYPE_PIPELINE_PUBLIC_ID
    _search_keys = ["name", "alternative_names"]
    _list_title = "Pipelines"
    _noun_plural = "pipelines"
    _add_label = "Pipeline"
    _url_prefix = "pipeline"
    _menu_groups = _blank_form_menu("indigo_admin_pipeline_download_blank_form")

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")


class AdminJoiningUpInitiativeList(AdminModelList):
    _model = JoiningUpInitiative
    _type_public_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID
    _search_keys = ["name"]
    _list_title = "Joining Up Initiatives"
    _noun_plural = "Joining Up Initiatives"
    _add_label = "Joining Up Initiative"
    _url_prefix = "joining_up_initiative"

    def has_permission(self):
        user = self.request.user
        return user.has_perm("indigo.admin")
