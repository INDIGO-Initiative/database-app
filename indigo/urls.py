from django.urls import path

from . import views

urlpatterns = [
    ########################### Home Page
    path("", views.index, name="indigo_index"),
    ########################### Public - Project
    path("project", views.projects_list, name="indigo_project_list",),
    path(
        "project_download",
        views.projects_list_download,
        name="indigo_project_list_download",
    ),
    path("project/<public_id>", views.project_index, name="indigo_project_index",),
    path(
        "project/<public_id>/download_form",
        views.project_download_form,
        name="indigo_project_download_form",
    ),
    ########################### Public - Project - API
    path("api1/project", views.api1_projects_list, name="indigo_api1_project_list",),
    path(
        "api1/project/<public_id>",
        views.api1_project_index,
        name="indigo_api1_project_index",
    ),
    ########################### Admin
    path("admin/", views.admin_index, name="indigo_admin_index"),
    ########################### Admin - Project
    path(
        "admin/project_download_blank_form",
        views.admin_project_download_blank_form,
        name="indigo_admin_project_download_blank_form",
    ),
    path("admin/project", views.admin_projects_list, name="indigo_admin_project_list",),
    path(
        "admin/project/<public_id>",
        views.admin_project_index,
        name="indigo_admin_project_index",
    ),
    path(
        "admin/project/<public_id>/make_private",
        views.admin_project_make_private,
        name="indigo_admin_project_make_private",
    ),
    path(
        "admin/project/<public_id>/make_disputed",
        views.admin_project_make_disputed,
        name="indigo_admin_project_make_disputed",
    ),
    path(
        "admin/project/<public_id>/download_form",
        views.admin_project_download_form,
        name="indigo_admin_project_download_form",
    ),
    path(
        "admin/project/<public_id>/import_form",
        views.admin_project_import_form,
        name="indigo_admin_project_import_form",
    ),
    path(
        "admin/project/<public_id>/import_form/<import_id>",
        views.admin_project_import_form_stage_2,
        name="indigo_admin_project_import_form_stage_2",
    ),
    path(
        "admin/project/<public_id>/moderate",
        views.admin_project_moderate,
        name="indigo_admin_project_moderate",
    ),
    path(
        "admin/project/<public_id>/history",
        views.admin_project_history,
        name="indigo_admin_project_history",
    ),
    path(
        "admin/new_project", views.admin_projects_new, name="indigo_admin_project_new",
    ),
    ########################### Admin - Organisation
    path(
        "admin/organisation_download_blank_form",
        views.admin_organisation_download_blank_form,
        name="indigo_admin_organisation_download_blank_form",
    ),
    path(
        "admin/organisation",
        views.admin_organisations_list,
        name="indigo_admin_organisation_list",
    ),
    path(
        "admin/organisation/<public_id>",
        views.admin_organisation_index,
        name="indigo_admin_organisation_index",
    ),
    path(
        "admin/organisation/<public_id>/download_form",
        views.admin_organisation_download_form,
        name="indigo_admin_organisation_download_form",
    ),
    path(
        "admin/organisation/<public_id>/import_form",
        views.admin_organisation_import_form,
        name="indigo_admin_organisation_import_form",
    ),
    path(
        "admin/organisation/<public_id>/moderate",
        views.admin_organisation_moderate,
        name="indigo_admin_organisation_moderate",
    ),
    path(
        "admin/organisation/<public_id>/history",
        views.admin_organisation_history,
        name="indigo_admin_organisation_history",
    ),
    path(
        "admin/new_organisation",
        views.admin_organisations_new,
        name="indigo_admin_organisation_new",
    ),
    ########################### Admin - Fund
    path(
        "admin/fund_download_blank_form",
        views.admin_fund_download_blank_form,
        name="indigo_admin_fund_download_blank_form",
    ),
    path("admin/fund", views.admin_funds_list, name="indigo_admin_fund_list",),
    path(
        "admin/fund/<public_id>",
        views.admin_fund_index,
        name="indigo_admin_fund_index",
    ),
    path(
        "admin/fund/<public_id>/download_form",
        views.admin_fund_download_form,
        name="indigo_admin_fund_download_form",
    ),
    path(
        "admin/fund/<public_id>/import_form",
        views.admin_fund_import_form,
        name="indigo_admin_fund_import_form",
    ),
    path(
        "admin/fund/<public_id>/moderate",
        views.admin_fund_moderate,
        name="indigo_admin_fund_moderate",
    ),
    path(
        "admin/fund/<public_id>/history",
        views.admin_fund_history,
        name="indigo_admin_fund_history",
    ),
    path("admin/new_fund", views.admin_funds_new, name="indigo_admin_fund_new",),
    ########################### Admin - Event
    path(
        "admin/event/<event_id>",
        views.admin_event_index,
        name="indigo_admin_event_index",
    ),
]
