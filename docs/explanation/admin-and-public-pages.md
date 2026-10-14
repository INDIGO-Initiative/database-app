# How the admin and public pages are built

The six types of record (project, organisation, fund, pipeline, assessment resource and joining up initiative) all have
the same pages, built from shared code and shared templates. The aim is that a change to how a page looks or works is
made once.

## URLs

* Public pages and the API are under `/app/` (the public home page is `/app/`; `/` redirects to it). External sites link
  to these, so they should not move.
* The admin pages of the app are under `/app/admin/`.
* Django's own admin is under `/admin/`.
* The JSON Data Ferret library's own pages (`/jsondataferret/...`) are not switched on. Old links to them redirect to the
  admin home page (`RetiredPageRedirect` in `djangoproject/views.py`).

## Admin views: `indigo/views_admin/`

The admin views are a package. `__init__.py` re-exports every view, so `urls.py` just says `views_admin.<name>`.

* `generic/` has the base class of each kind of page that every type of record has. The behaviour is here, so a change
  to how a page works for every type is made in one place.

  | Module | The page |
  |---|---|
  | `generic/lists.py`, `generic/records.py` | The list page and the page of one record |
  | `generic/new.py`, `generic/edit.py` | Adding a record and editing it with the web form |
  | `generic/change_status.py`, `generic/moderate.py` | Changing a record's status; approving or rejecting waiting edits |
  | `generic/history.py`, `generic/data_quality.py` | The History page and the data quality report of one record |
  | `generic/imports.py`, `generic/downloads.py` | Spreadsheet import (one stage, or two for big forms) and downloads |

* One module for each type: `project.py`, `organisation.py`, `fund.py`, `pipeline.py`, `assessment_resource.py` and
  `joining_up_initiative.py`. Each has a small subclass of each base class, which only sets class variables (its model,
  its words such as `_list_title`, its permissions), and the views that only that type has. Everything about one type,
  including who is allowed to do what with it, is in its module.
* `common.py` has helpers used by the others: `RECORD_TITLES`, `subpage_context`, `edit_changes`, the permission checks.
* `dashboard.py`, `to_moderate.py`, `events.py` (the site-wide History page and the pages for one event or edit) and
  `sandboxes.py` are the admin pages that are not about one type.

The base classes never import from the type modules.

Projects and organisations use the same base classes as the other types. Where they differ, the base class has a hook
that the subclass overrides: `_get_items` (what a list shows: a data steward only lists the projects they have access
to), `_check_access` (the `ProjectAccessMixin`, which stops a data steward opening another project's pages),
`_after_create` (giving a steward access to a project they have just added) and `_get_import_json` (how an uploaded
spreadsheet is read: there are several versions of the organisation form).

## Admin templates: `indigo/templates/indigo/admin/`

There are no templates for individual types. Each page has one template:

* `list.html`, `record.html`, `edit.html`, `new.html`, `moderate.html`, `change_status.html`, `record_history.html`,
  `related_records.html`, `data_quality_report.html`, and the import pages (`import_form.html`, `import_stage_2.html`,
  `import_message.html`).
* Pages about one record extend `record_subpage.html`, which makes the breadcrumbs (Admin > list > record > this page).
  Their views make the context with `subpage_context(record, ...)`, which gives the record, the type's titles and the
  links back.
* Shared pieces are in `admin/includes/` (the simple form, the moderation table, the data quality errors) and
  `indigo/includes/` (the page header, actions menu, comment box, result count, history table, user menu, footer).
  The public pages use the ones in `indigo/includes/` too, so the admin and public sites look the same.

## Record pages and the edit form

A record page (`indigo/recordpages.py`) turns the record's data into sections with a sidebar. The edit form uses the same
sections as tabs. Both read `indigo/section_groups.json`, which says which parts of a type's data go in which section.
A type with no entry there gets a "General" section and one section for each repeating list.

The edit form is a React JSON Schema Form (see [Rebuild the frontend](../how-to-guide/rebuild-frontend.md)). Django
checks the whole record against the type's schema when it is saved, and the edit always goes to moderation. This is the
same as uploading a spreadsheet.

## What a type needs

Fund is the simplest type to copy. A type needs:

* A model, and its entry in `JSONDATAFERRET_TYPE_INFORMATION` (the schema, the fields, and the spreadsheet form).
* A `Type` record in the database, and constants in `indigo/__init__.py`. The type's public id (`fund`, ...) is also the
  start of its admin URL names (`indigo_admin_fund_list`), and the views and templates rely on that.
* Its titles in `RECORD_TITLES` in `views_admin/common.py`.
* A module for it in `indigo/views_admin/` (copy `fund.py`) with a subclass for each admin page (`AdminFundList`,
  `AdminFundIndex`, `AdminFundEdit`, `AdminFundNew`, `AdminFundModerate`, `AdminFundChangeStatus`, `AdminFundHistory`, and
  the spreadsheet downloads and import if it has a spreadsheet form), and the matching routes in `urls.py`.
* Its edit and add forms in `indigo/forms.py` (`FundEditForm`, `FundNewForm`).
* Optionally, tab groups in `indigo/section_groups.json`. Rebuild the frontend after changing that file.

Every admin route must be locked to the right permission. `indigo/tests/test_admin_permissions.py` walks all the admin
routes to check that anonymous users and users without the permission are refused, so a new route is checked
automatically.

## Tests

* Run them with `django-admin test indigo` (in Docker: `docker compose run --rm web django-admin test indigo --noinput`).
  A harmless "cannot drop the currently open database" error at the very end is a clean-up message, not a failure.
* `indigo/tests/__init__.py` stops the tests queuing real Celery tasks and sends file storage to a temporary
  directory. Without that, a running worker would pick up tasks for the development database and write spreadsheets into
  the project's `public/` folder.
