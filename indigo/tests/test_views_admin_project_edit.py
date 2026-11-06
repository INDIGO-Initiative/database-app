import datetime
import json
import urllib.parse

import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase  # noqa
from django.utils import timezone
from django.urls import reverse

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import AdminUserHasPermissionsForProject, Fund, Organisation, Project
from indigo.spreadsheetforms import extract_edits_from_form


class AdminProjectEditTests(TestCase):
    def setUp(self):
        self.type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        self.record = jsondataferret.models.Record.objects.create(
            type=self.type_project, public_id="PROJ1"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    self.type_project,
                    self.record,
                    {
                        "name": {"value": "Old name"},
                        "notes": {"value": "Some notes"},
                        "documents": [{"title": {"value": "Doc 1"}}],
                    },
                    approved=True,
                )
            ]
        )
        self.record.refresh_from_db()
        self.url = reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ1"})

    def _user(self, codename):
        user = User.objects.create_user(username=codename, password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename=codename)
        )
        return user

    def test_removed_values_become_null_and_lists_are_replaced(self):
        edits = extract_edits_from_form(
            TYPE_PROJECT_PUBLIC_ID,
            self.record,
            {"name": {"value": "New name"}, "documents": []},
        )
        new_data = edits[
            0
        ].get_new_data_when_event_applied_to_latest_record_cached_data()
        self.assertEqual(new_data["name"]["value"], "New name")
        self.assertIsNone(new_data["notes"])
        self.assertEqual(new_data["documents"], [])

    def test_admin_can_see_form(self):
        self._user("admin")
        self.client.login(username="admin", password="1234")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_form_loads_rjsf_bundle_and_current_data(self):
        self._user("admin")
        self.client.login(username="admin", password="1234")
        content = self.client.get(self.url).content.decode()
        self.assertIn("rjsf/rjsf-form.js", content)
        self.assertIn('class="rjsf-holder"', content)
        # Current data is in the hidden field as JSON
        self.assertIn("&quot;Old name&quot;", content)

    def test_data_steward_without_access_is_refused(self):
        self._user("data_steward")
        self.client.login(username="data_steward", password="1234")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)

    def test_post_creates_edit_needing_moderation(self):
        self._user("admin")
        self.client.login(username="admin", password="1234")
        response = self.client.post(
            self.url,
            {
                "data": json.dumps({"name": {"value": "New name"}}),
                "comment": "Test",
            },
        )
        self.assertEqual(response.status_code, 302)
        edit = jsondataferret.models.Edit.objects.filter(
            record=self.record, approval_event=None
        ).get()
        self.assertIsNone(edit.refusal_event)
        # Not live until moderated
        self.assertEqual(
            Project.objects.get(public_id="PROJ1").data_private["name"]["value"],
            "Old name",
        )

    def test_invalid_data_is_rejected(self):
        self._user("admin")
        self.client.login(username="admin", password="1234")
        response = self.client.post(
            self.url,
            {"data": json.dumps({"name": "just text", "bogus": 1}), "comment": "T"},
        )
        self.assertEqual(response.status_code, 200)
        # Errors say where the problem is
        self.assertContains(response, "/name: &#x27;just text&#x27; is not of type")
        self.assertContains(response, '"path": "/name"')
        self.assertContains(response, 'id="id_data_errors"')
        self.assertFalse(
            jsondataferret.models.Edit.objects.filter(
                record=self.record, approval_event=None
            ).exists()
        )


class AdminOrganisationSearchJSONTests(TestCase):
    def setUp(self):
        self.type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        for id, name in [("ORG1", "Acme Trust"), ("ORG2", "Other Charity")]:
            Organisation.objects.create(
                public_id=id,
                data_private={"name": {"value": name}},
                full_text_search_private=name,
            )
        self.url = reverse("indigo_admin_organisation_search_json")

    def _login(self, codename):
        user = User.objects.create_user(username=codename, password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename=codename)
        )
        self.client.login(username=codename, password="1234")

    def test_look_up_by_ids(self):
        self._login("admin")
        response = self.client.get(self.url, {"ids": "ORG2, ORG1"})
        self.assertEqual(
            response.json()["results"],
            [
                {"id": "ORG1", "name": "Acme Trust"},
                {"id": "ORG2", "name": "Other Charity"},
            ],
        )

    def test_search_by_name(self):
        self._login("data_steward")
        response = self.client.get(self.url, {"search": "Acme"})
        self.assertEqual(
            response.json()["results"], [{"id": "ORG1", "name": "Acme Trust"}]
        )

    def test_no_query_returns_nothing(self):
        self._login("admin")
        self.assertEqual(self.client.get(self.url).json()["results"], [])

    def test_anonymous_is_refused(self):
        self.assertNotEqual(self.client.get(self.url).status_code, 200)


class AdminOtherFormsTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")

    def _make_record(self, type_public_id, record_public_id, data):
        type = jsondataferret.models.Type.objects.create(
            public_id=type_public_id, title=type_public_id
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id=record_public_id
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type, record, data, approved=True
                )
            ]
        )
        record.refresh_from_db()
        return record

    def test_organisation_edit_removes_cleared_values_after_moderation(self):
        record = self._make_record(
            TYPE_ORGANISATION_PUBLIC_ID,
            "ORG1",
            {"name": {"value": "Old"}, "website": {"value": "https://example.com"}},
        )
        url = reverse("indigo_admin_organisation_edit", kwargs={"public_id": "ORG1"})
        self.assertContains(self.client.get(url), 'class="rjsf-holder"')

        response = self.client.post(
            url, {"data": json.dumps({"name": {"value": "New"}}), "comment": "Test"}
        )
        self.assertEqual(response.status_code, 302)

        edit = jsondataferret.models.Edit.objects.get(
            record=record, approval_event=None
        )
        new_data = edit.get_new_data_when_edit_applied_to_latest_record_cached_data()
        self.assertEqual(new_data["name"]["value"], "New")
        self.assertIsNone(new_data["website"])
        self.assertEqual(record.cached_data["name"]["value"], "Old")

    def test_joining_up_initiative_forms_load(self):
        self._make_record(
            TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
            "JUI1",
            {"name": {"value": "Initiative"}},
        )
        for url in [
            reverse("indigo_admin_joining_up_initiative_new"),
            reverse(
                "indigo_admin_joining_up_initiative_edit", kwargs={"public_id": "JUI1"}
            ),
        ]:
            self.assertContains(self.client.get(url), 'class="rjsf-holder"')

    def test_joining_up_initiative_edit_checks_schema(self):
        self._make_record(
            TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
            "JUI1",
            {"name": {"value": "Initiative"}},
        )
        url = reverse(
            "indigo_admin_joining_up_initiative_edit", kwargs={"public_id": "JUI1"}
        )
        # The schema requires several things that are missing here
        response = self.client.post(
            url, {"data": json.dumps({"name": {"value": "x"}}), "comment": "Test"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        # Each problem says which field it is about, so the form can show it there
        self.assertContains(response, '"path": "/dates"')

    def test_fund_pipeline_and_assessment_resource_edit_forms_load(self):
        for type_id, public_id, view in [
            (TYPE_FUND_PUBLIC_ID, "FUND1", "indigo_admin_fund_edit"),
            (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "indigo_admin_pipeline_edit"),
            (
                TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
                "ARES1",
                "indigo_admin_assessment_resource_edit",
            ),
        ]:
            self._make_record(type_id, public_id, {"name": {"value": "Thing"}})
            response = self.client.get(reverse(view, kwargs={"public_id": public_id}))
            self.assertContains(response, 'class="rjsf-holder"')
            self.assertContains(response, "&quot;Thing&quot;")

    def test_edit_buttons_on_lists(self):
        self._make_record(TYPE_FUND_PUBLIC_ID, "FUND1", {"name": {"value": "A fund"}})
        self._make_record(TYPE_PROJECT_PUBLIC_ID, "PROJ1", {"name": {"value": "P"}})
        self.assertContains(
            self.client.get(reverse("indigo_admin_fund_list")),
            reverse("indigo_admin_fund_edit", kwargs={"public_id": "FUND1"}),
        )
        response = self.client.get(reverse("indigo_admin_project_list"))
        self.assertContains(
            response,
            reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ1"}),
        )
        self.assertContains(response, reverse("indigo_admin_project_new"))

    def test_data_steward_can_edit_funds_but_not_pipelines(self):
        self._make_record(TYPE_FUND_PUBLIC_ID, "FUND1", {"name": {"value": "A fund"}})
        self._make_record(TYPE_PIPELINE_PUBLIC_ID, "PIPE1", {"name": {"value": "P"}})
        self.client.logout()
        user = User.objects.create_user(username="steward", password="1234")
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="indigo", codename="data_steward"
            )
        )
        self.client.login(username="steward", password="1234")
        self.assertEqual(
            self.client.get(
                reverse("indigo_admin_fund_edit", kwargs={"public_id": "FUND1"})
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("indigo_admin_pipeline_edit", kwargs={"public_id": "PIPE1"})
            ).status_code,
            403,
        )

    def test_creating_a_fund_goes_straight_to_its_edit_form(self):
        jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        response = self.client.post(
            reverse("indigo_admin_fund_new"), {"name": "New fund", "comment": "Created"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith("/edit"), response.url)

    def test_record_pages_have_edit_and_a_menu_of_actions_at_the_top(self):
        records = [
            (TYPE_PROJECT_PUBLIC_ID, "PROJ1", "project"),
            (TYPE_ORGANISATION_PUBLIC_ID, "ORG1", "organisation"),
            (TYPE_FUND_PUBLIC_ID, "FUND1", "fund"),
            (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "pipeline"),
            (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "ARES1", "assessment_resource"),
            (TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID, "JUI1", "joining_up_initiative"),
        ]
        for type_id, public_id, name in records:
            self._make_record(type_id, public_id, {"name": {"value": "Thing"}})
            index = self.client.get(
                reverse(f"indigo_admin_{name}_index", kwargs={"public_id": public_id})
            )
            self.assertEqual(index.status_code, 200, name)
            content = index.content.decode()
            table = content.index("<table")
            # Edit is a button, and the other actions are in a menu; both come before the details
            edit = reverse(f"indigo_admin_{name}_edit", kwargs={"public_id": public_id})
            self.assertLess(content.index(edit), table, name)
            menu = content[content.index("dropdown-menu") : table]
            for action in ["change_status", "moderate", "history"]:
                url = reverse(
                    f"indigo_admin_{name}_{action}", kwargs={"public_id": public_id}
                )
                self.assertIn(url, menu, f"{name} {action}")
                # and no longer a row of buttons
                self.assertEqual(content.count(f'href="{url}"'), 1, f"{name} {action}")
            self.assertNotIn("btn btn-primary mb-2", content, name)
            # The title and the buttons are laid out so a long title can't push the buttons below it
            self.assertIn('class="record-header', content, name)
            self.assertIn('class="record-header__title"', content, name)
            self.assertIn('class="record-header__actions"', content, name)
            self.assertNotIn("flex-wrap justify-content-between", content, name)
            # Spreadsheet downloads are under their own heading in the menu
            if name != "joining_up_initiative":
                self.assertIn("Spreadsheets", menu, name)
                self.assertIn(
                    reverse(
                        f"indigo_admin_{name}_download_form",
                        kwargs={"public_id": public_id},
                    ),
                    menu,
                    name,
                )
        # Related lists are only offered to admins
        fund_index = reverse("indigo_admin_fund_index", kwargs={"public_id": "FUND1"})
        fund_projects = reverse(
            "indigo_admin_fund_projects", kwargs={"public_id": "FUND1"}
        )
        self.assertContains(self.client.get(fund_index), fund_projects)
        self.client.logout()
        steward = User.objects.create_user(username="steward", password="1234")
        steward.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="indigo", codename="data_steward"
            )
        )
        self.client.login(username="steward", password="1234")
        self.assertNotContains(self.client.get(fund_index), fund_projects)
        self.client.logout()
        self.client.login(username="admin", password="1234")
        for name in ["project", "fund", "pipeline", "assessment_resource"]:
            self.assertEqual(
                self.client.get(reverse(f"indigo_admin_{name}_list")).status_code, 200
            )
        for url in [
            reverse("indigo_admin_organisation_list"),
            reverse("indigo_admin_organisation_search"),
        ]:
            self.assertContains(
                self.client.get(url), reverse("indigo_admin_organisation_new")
            )


class AdminEditPermissionTests(TestCase):
    """Nobody can see or submit these forms without the right permission, and a rejected submit saves nothing."""

    EDIT_VIEWS = [
        # type, record id, view name, who may use it
        (
            TYPE_PROJECT_PUBLIC_ID,
            "PROJ1",
            "indigo_admin_project_edit",
            "admin or steward",
        ),
        (
            TYPE_ORGANISATION_PUBLIC_ID,
            "ORG1",
            "indigo_admin_organisation_edit",
            "admin or steward",
        ),
        (TYPE_FUND_PUBLIC_ID, "FUND1", "indigo_admin_fund_edit", "admin or steward"),
        (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "indigo_admin_pipeline_edit", "admin"),
        (
            TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
            "ARES1",
            "indigo_admin_assessment_resource_edit",
            "admin",
        ),
        (
            TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
            "JUI1",
            "indigo_admin_joining_up_initiative_edit",
            "admin",
        ),
    ]
    POST_DATA = {"data": json.dumps({"name": {"value": "Hacked"}}), "comment": "x"}

    def setUp(self):
        for type_id, public_id, view, who in self.EDIT_VIEWS:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            record = jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id
            )
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type, record, {"name": {"value": "Original"}}, approved=True
                    )
                ]
            )

    def _login(self, codename=None):
        user = User.objects.create_user(username=codename or "nobody", password="1234")
        if codename:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="indigo", codename=codename
                )
            )
        self.client.login(username=user.username, password="1234")
        return user

    def _assert_refused(self, url):
        get = self.client.get(url)
        self.assertIn(get.status_code, (302, 403), url)
        post = self.client.post(url, self.POST_DATA)
        self.assertIn(post.status_code, (302, 403), url)
        self.assertEqual(
            jsondataferret.models.Edit.objects.filter(approval_event=None).count(),
            0,
            f"{url} saved an edit for a user who should be refused",
        )

    def _url(self, view, public_id):
        return reverse(view, kwargs={"public_id": public_id})

    def test_anonymous_users_are_refused_everywhere(self):
        for type_id, public_id, view, who in self.EDIT_VIEWS:
            self._assert_refused(self._url(view, public_id))
            # Sent to the login page, not shown anything
            self.assertEqual(
                self.client.get(self._url(view, public_id)).status_code, 302
            )
        self._assert_refused(reverse("indigo_admin_joining_up_initiative_new"))
        self.assertEqual(
            self.client.get(
                reverse("indigo_admin_organisation_search_json")
            ).status_code,
            302,
        )

    def test_users_with_no_permissions_are_refused_everywhere(self):
        self._login()
        for type_id, public_id, view, who in self.EDIT_VIEWS:
            self._assert_refused(self._url(view, public_id))
        self._assert_refused(reverse("indigo_admin_joining_up_initiative_new"))
        self.assertIn(
            self.client.get(
                reverse("indigo_admin_organisation_search_json")
            ).status_code,
            (302, 403),
        )

    def test_data_stewards_are_refused_admin_only_forms(self):
        self._login("data_steward")
        for type_id, public_id, view, who in self.EDIT_VIEWS:
            if who == "admin":
                self._assert_refused(self._url(view, public_id))
        self._assert_refused(reverse("indigo_admin_joining_up_initiative_new"))

    def test_data_steward_cannot_edit_a_project_they_have_no_access_to(self):
        self._login("data_steward")
        url = self._url("indigo_admin_project_edit", "PROJ1")
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.POST_DATA).status_code, 403)
        self.assertFalse(
            jsondataferret.models.Edit.objects.filter(approval_event=None).exists()
        )

    def test_data_steward_can_edit_a_project_they_have_access_to(self):
        user = self._login("data_steward")
        AdminUserHasPermissionsForProject.objects.create(
            user=user,
            project=Project.objects.get(public_id="PROJ1"),
            permission_access=True,
        )
        url = self._url("indigo_admin_project_edit", "PROJ1")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, self.POST_DATA).status_code, 302)

    def test_a_steward_whose_access_was_switched_off_is_refused(self):
        user = self._login("data_steward")
        AdminUserHasPermissionsForProject.objects.create(
            user=user,
            project=Project.objects.get(public_id="PROJ1"),
            permission_access=False,
        )
        self.assertEqual(
            self.client.get(
                self._url("indigo_admin_project_edit", "PROJ1")
            ).status_code,
            403,
        )

    def test_a_submit_without_a_csrf_token_is_refused(self):
        self._login("admin")
        client = Client(enforce_csrf_checks=True)
        client.login(username="admin", password="1234")
        response = client.post(
            self._url("indigo_admin_project_edit", "PROJ1"), self.POST_DATA
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            jsondataferret.models.Edit.objects.filter(approval_event=None).exists()
        )


class AdminListPaginationTests(TestCase):
    def _login(self, codename):
        user = User.objects.create_user(username=codename, password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename=codename)
        )
        self.client.login(username=codename, password="1234")
        return user

    def _make_organisations(self, count, name="Acme"):
        for i in range(count):
            Organisation.objects.create(
                public_id=f"INDIGO-ORG-{i:04d}",
                data_private={"name": {"value": f"{name} {i}"}},
                full_text_search_private=f"{name} {i}",
            )

    def test_organisation_search_is_split_into_pages(self):
        self._login("admin")
        self._make_organisations(120)
        url = reverse("indigo_admin_organisation_search")

        first = self.client.get(url)
        self.assertEqual(len(first.context["items"]), 100)
        self.assertContains(first, "Page 1 of 2")
        self.assertContains(
            first, "Showing 1&ndash;100 of <strong>120</strong> results"
        )
        self.assertContains(first, "INDIGO-ORG-0000")
        self.assertNotContains(first, "INDIGO-ORG-0100")

        second = self.client.get(url, {"page": 2})
        self.assertContains(
            second, "Showing 101&ndash;120 of <strong>120</strong> results"
        )
        self.assertEqual(len(second.context["items"]), 20)
        self.assertContains(second, "INDIGO-ORG-0100")
        self.assertNotContains(second, "INDIGO-ORG-0000")

    def test_search_term_is_kept_in_the_page_links(self):
        self._login("admin")
        self._make_organisations(120)
        response = self.client.get(
            reverse("indigo_admin_organisation_search"), {"search": "Acme"}
        )
        self.assertContains(response, "?search=Acme&amp;page=2")

    def test_odd_page_numbers_do_not_break_the_page(self):
        self._login("admin")
        self._make_organisations(120)
        url = reverse("indigo_admin_organisation_search")
        self.assertContains(self.client.get(url, {"page": "banana"}), "Page 1 of 2")
        self.assertContains(self.client.get(url, {"page": 99}), "Page 2 of 2")

    def test_a_short_list_has_no_page_links(self):
        self._login("admin")
        self._make_organisations(3)
        response = self.client.get(reverse("indigo_admin_organisation_search"))
        self.assertNotContains(response, "Page 1 of")

    def test_funds_list_is_split_into_pages(self):
        self._login("admin")
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        for i in range(105):
            jsondataferret.models.Record.objects.create(
                type=type, public_id=f"INDIGO-FUND-{i:04d}"
            )
        response = self.client.get(reverse("indigo_admin_fund_list"))
        self.assertEqual(len(response.context["items"]), 100)
        self.assertContains(response, "Page 1 of 2")
        self.assertEqual(
            len(
                self.client.get(reverse("indigo_admin_fund_list"), {"page": 2}).context[
                    "items"
                ]
            ),
            5,
        )

    def test_project_list_is_paged_for_admins_and_stewards(self):
        self._login("admin")
        for i in range(120):
            Project.objects.create(public_id=f"INDIGO-POJ-{i:04d}")
        url = reverse("indigo_admin_project_list")
        self.assertEqual(len(self.client.get(url).context["items"]), 100)
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["items"]), 20)

        # A data steward's list comes from a raw query, and only has their projects
        self.client.logout()
        steward = self._login("data_steward")
        for i in (3, 7):
            AdminUserHasPermissionsForProject.objects.create(
                user=steward,
                project=Project.objects.get(public_id=f"INDIGO-POJ-{i:04d}"),
                permission_access=True,
            )
        response = self.client.get(url)
        self.assertEqual(
            [p.public_id for p in response.context["items"]],
            ["INDIGO-POJ-0003", "INDIGO-POJ-0007"],
        )
        self.assertNotContains(response, "Page 1 of")

    def test_project_list_can_be_searched_by_id_or_name(self):
        self._login("admin")
        Project.objects.create(
            public_id="INDIGO-POJ-0001",
            data_private={"name": {"value": "Peterborough Social Impact Bond"}},
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0002",
            data_private={
                "name": {"value": "Homeless Pathways"},
                "alternative_names": {"value": "Rough sleeping fund"},
            },
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0013", data_private={"name": {"value": "Other"}}
        )
        url = reverse("indigo_admin_project_list")

        def ids(search):
            response = self.client.get(url, {"search": search})
            return [p.public_id for p in response.context["items"]]

        self.assertEqual(ids("peterborough"), ["INDIGO-POJ-0001"])
        self.assertEqual(ids("PATHWAYS"), ["INDIGO-POJ-0002"])
        self.assertEqual(ids("rough sleeping"), ["INDIGO-POJ-0002"])
        self.assertEqual(ids("POJ-0013"), ["INDIGO-POJ-0013"])
        self.assertEqual(len(ids("")), 3)
        self.assertEqual(ids("nothing like this"), [])
        self.assertContains(
            self.client.get(url, {"search": "nothing like this"}),
            "No projects match your search",
        )
        self.assertContains(self.client.get(url, {"search": "peter"}), 'value="peter"')

    def test_a_steward_only_finds_their_own_projects(self):
        steward = self._login("data_steward")
        mine = Project.objects.create(
            public_id="INDIGO-POJ-0001", data_private={"name": {"value": "Shared name"}}
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0002", data_private={"name": {"value": "Shared name"}}
        )
        AdminUserHasPermissionsForProject.objects.create(
            user=steward, project=mine, permission_access=True
        )
        response = self.client.get(
            reverse("indigo_admin_project_list"), {"search": "shared"}
        )
        self.assertEqual(
            [p.public_id for p in response.context["items"]], ["INDIGO-POJ-0001"]
        )

    def test_project_list_actions_are_in_a_menu_at_the_top(self):
        self._login("admin")
        Project.objects.create(public_id="INDIGO-POJ-0001")
        response = self.client.get(reverse("indigo_admin_project_list"))
        content = response.content.decode()
        menu = content[content.index("dropdown-menu") : content.index("<table")]
        for url_name in [
            "indigo_admin_all_projects_data_quality_report",
            "indigo_admin_project_download_blank_form",
            "indigo_admin_project_download_blank_simple_form",
        ]:
            self.assertIn(reverse(url_name), menu)
        # The menu comes before the list, and there is no row of buttons left under it
        self.assertLess(content.index("dropdown-menu"), content.index("<table"))
        self.assertEqual(content.count(reverse("indigo_admin_project_new")), 1)

    def test_data_quality_report_is_only_in_the_menu_for_admins(self):
        self._login("data_steward")
        response = self.client.get(reverse("indigo_admin_project_list"))
        self.assertNotContains(
            response, reverse("indigo_admin_all_projects_data_quality_report")
        )
        self.assertContains(
            response, reverse("indigo_admin_project_download_blank_form")
        )

    def test_organisation_list_is_the_search_page_with_a_menu(self):
        self._login("admin")
        self._make_organisations(3)
        url = reverse("indigo_admin_organisation_list")
        response = self.client.get(url)
        self.assertContains(response, "INDIGO-ORG-0001")
        self.assertContains(response, reverse("indigo_admin_organisation_new"))
        self.assertContains(response, reverse("indigo_admin_organisation_goto"))
        # Downloads are in a menu at the top, before the list
        content = response.content.decode()
        self.assertLess(content.index("dropdown-menu"), content.index("<table"))
        for url_name in [
            "indigo_admin_organisation_download_blank_form",
            "indigo_admin_organisation_download_all_csv",
        ]:
            self.assertContains(response, reverse(url_name))
        # The pointless landing page is gone, and the old search address still works
        self.assertNotContains(response, "List / Search")
        self.assertContains(
            self.client.get(reverse("indigo_admin_organisation_search")),
            "INDIGO-ORG-0001",
        )
        # Searching and paging work from the list address
        self.assertEqual(
            len(self.client.get(url, {"search": "Acme 1"}).context["items"]), 1
        )

    def test_other_lists_have_add_and_a_menu_at_the_top(self):
        self._login("admin")
        for type_id, public_id, name, menu_urls in [
            (
                TYPE_FUND_PUBLIC_ID,
                "FUND1",
                "fund",
                ["indigo_admin_fund_download_blank_form"],
            ),
            (
                TYPE_PIPELINE_PUBLIC_ID,
                "PIPE1",
                "pipeline",
                ["indigo_admin_pipeline_download_blank_form"],
            ),
            (
                TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
                "ARES1",
                "assessment_resource",
                ["indigo_admin_assessment_resource_download_blank_form"],
            ),
            (TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID, "JUI1", "joining_up_initiative", []),
        ]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            jsondataferret.models.Record.objects.create(type=type, public_id=public_id)
            response = self.client.get(reverse(f"indigo_admin_{name}_list"))
            content = response.content.decode()
            add_url = reverse(f"indigo_admin_{name}_new")
            # One Add button, at the top, before the list
            self.assertEqual(content.count(f'href="{add_url}"'), 1, name)
            self.assertLess(content.index(add_url), content.index("<table"), name)
            for url_name in menu_urls:
                self.assertIn(reverse(url_name), content, name)
                self.assertLess(content.index("dropdown-menu"), content.index("<table"))
            if not menu_urls:
                # (The top bar has the user's menu, so look only at the page below it)
                page = content[content.index('<div class="record-header') :]
                self.assertNotIn("dropdown-menu", page, name)

    def test_pipeline_list_can_be_searched(self):
        self._login("admin")
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PIPELINE_PUBLIC_ID, title="Pipeline"
        )
        for public_id, data in [
            ("INDIGO-PL-0001", {"name": {"value": "Northern Employment Pipeline"}}),
            (
                "INDIGO-PL-0002",
                {
                    "name": {"value": "Housing"},
                    "alternative_names": {"value": "Warm Homes Scheme"},
                },
            ),
            ("INDIGO-PL-0013", {"name": {"value": "Other"}}),
        ]:
            jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id, cached_data=data
            )
        url = reverse("indigo_admin_pipeline_list")

        def ids(search):
            return [
                r.public_id
                for r in self.client.get(url, {"search": search}).context["items"]
            ]

        self.assertEqual(ids("northern"), ["INDIGO-PL-0001"])
        self.assertEqual(ids("warm homes"), ["INDIGO-PL-0002"])
        self.assertEqual(ids("PL-0013"), ["INDIGO-PL-0013"])
        self.assertEqual(len(ids("")), 3)
        self.assertEqual(ids("zzz"), [])
        self.assertContains(
            self.client.get(url, {"search": "zzz"}), "No pipelines match your search"
        )
        self.assertContains(self.client.get(url, {"search": "north"}), 'value="north"')

    def test_every_list_can_be_searched_by_id_or_name(self):
        self._login("admin")
        for type_id, name, id_prefix in [
            (TYPE_FUND_PUBLIC_ID, "fund", "INDIGO-FUND"),
            (TYPE_PIPELINE_PUBLIC_ID, "pipeline", "INDIGO-PL"),
            (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "assessment_resource", "INDIGO-ARES"),
            (
                TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
                "joining_up_initiative",
                "INDIGO-JUI",
            ),
        ]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            for i, thing_name in [(1, "Alpha Thing"), (2, "Beta Thing")]:
                jsondataferret.models.Record.objects.create(
                    type=type,
                    public_id=f"{id_prefix}-000{i}",
                    cached_data={"name": {"value": thing_name}},
                )
            url = reverse(f"indigo_admin_{name}_list")

            def ids(search):
                return [
                    r.public_id
                    for r in self.client.get(url, {"search": search}).context["items"]
                ]

            self.assertEqual(ids("alpha"), [f"{id_prefix}-0001"], name)
            self.assertEqual(ids("0002"), [f"{id_prefix}-0002"], name)
            self.assertEqual(len(ids("thing")), 2, name)
            self.assertEqual(ids("zzz"), [], name)
            response = self.client.get(url, {"search": "zzz"})
            self.assertContains(response, "match your search", msg_prefix=name)
            self.assertContains(response, 'value="zzz"', msg_prefix=name)
            self.assertContains(response, "Clear", msg_prefix=name)

    def test_history_pages_show_the_newest_edits_first(self):
        self._login("admin")
        for type_id, public_id, name in [
            (TYPE_PROJECT_PUBLIC_ID, "PROJ1", "project"),
            (TYPE_ORGANISATION_PUBLIC_ID, "ORG1", "organisation"),
            (TYPE_FUND_PUBLIC_ID, "FUND1", "fund"),
            (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "pipeline"),
            (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "ARES1", "assessment_resource"),
            (TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID, "JUI1", "joining_up_initiative"),
        ]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            record = jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id
            )
            for comment in ["first", "second", "third"]:
                jsondataferret.pythonapi.newevent.newEvent(
                    [
                        jsondataferret.pythonapi.newevent.NewEventData(
                            type, record, {"name": {"value": comment}}, approved=True
                        )
                    ],
                    comment=comment,
                )
            response = self.client.get(
                reverse(f"indigo_admin_{name}_history", kwargs={"public_id": public_id})
            )
            self.assertEqual(
                [event.comment for event in response.context["page_obj"]],
                ["third", "second", "first"],
                name,
            )
            content = response.content.decode()
            self.assertLess(content.index("third"), content.index("first"), name)
            # Each row's button says what it opens
            self.assertContains(response, ">View change</a>", msg_prefix=name)
            self.assertNotContains(response, ">View</a>", msg_prefix=name)

    def test_site_wide_history_shows_the_newest_events_first(self):
        self._login("admin")
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id="FUND1"
        )
        for comment in ["first", "second", "third"]:
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type, record, {"name": {"value": comment}}, approved=True
                    )
                ],
                comment=comment,
            )
        response = self.client.get(reverse("indigo_admin_history"))
        self.assertEqual(
            [event.comment for event in response.context["page_obj"]],
            ["third", "second", "first"],
        )


class AdminDashboardTests(TestCase):
    def _login(self, codename):
        user = User.objects.create_user(username=codename, password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename=codename)
        )
        self.client.login(username=codename, password="1234")
        return user

    def _record_with_pending_edit(self, type_id, public_id):
        type, _ = jsondataferret.models.Type.objects.get_or_create(
            public_id=type_id, defaults={"title": type_id}
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id=public_id
        )
        newEvent = jsondataferret.pythonapi.newevent.newEvent
        NewEventData = jsondataferret.pythonapi.newevent.NewEventData
        newEvent([NewEventData(type, record, {"name": {"value": "A"}}, approved=True)])
        newEvent([NewEventData(type, record, {"name": {"value": "B"}})])

    def test_admin_sees_every_section_with_counts_and_a_moderation_banner(self):
        self._login("admin")
        self._record_with_pending_edit(TYPE_PROJECT_PUBLIC_ID, "PROJ1")
        self._record_with_pending_edit(TYPE_FUND_PUBLIC_ID, "FUND1")
        Project.objects.create(public_id="PROJ2")
        response = self.client.get(reverse("indigo_admin_index"))
        self.assertEqual(response.status_code, 200)
        sections = {s["title"]: s for s in response.context["sections"]}
        self.assertEqual(
            list(sections),
            [
                "Projects",
                "Organisations",
                "Funds",
                "Pipelines",
                "Assessment Resources",
                "Joining Up Initiatives",
            ],
        )
        self.assertEqual(sections["Projects"]["count"], 2)
        self.assertEqual(sections["Projects"]["waiting"], 1)
        self.assertEqual(sections["Funds"]["waiting"], 1)
        self.assertEqual(sections["Organisations"]["waiting"], 0)
        self.assertEqual(response.context["waiting_total"], 2)
        self.assertContains(response, "2</strong> records with changes waiting")
        self.assertContains(response, reverse("indigo_admin_to_moderate"))
        self.assertContains(response, reverse("indigo_admin_history"))
        # Each section links to its list, and to adding one
        for section in sections.values():
            self.assertContains(response, reverse(section["list_url"]))
            self.assertContains(response, reverse(section["new_url"]))

    def test_admin_is_told_when_nothing_is_waiting(self):
        self._login("admin")
        response = self.client.get(reverse("indigo_admin_index"))
        self.assertContains(response, "Nothing is waiting to be moderated")
        self.assertNotContains(response, "waiting to be moderated.</span>")

    def test_data_steward_sees_only_their_sections(self):
        steward = self._login("data_steward")
        mine = Project.objects.create(public_id="PROJ1")
        Project.objects.create(public_id="PROJ2")
        AdminUserHasPermissionsForProject.objects.create(
            user=steward, project=mine, permission_access=True
        )
        response = self.client.get(reverse("indigo_admin_index"))
        sections = {s["title"]: s for s in response.context["sections"]}
        self.assertEqual(list(sections), ["Projects", "Organisations", "Funds"])
        # Only the projects they can see are counted
        self.assertEqual(sections["Projects"]["count"], 1)
        # The moderation tools and history are for admins
        self.assertIsNone(response.context["waiting_total"])
        self.assertNotContains(response, reverse("indigo_admin_to_moderate"))
        self.assertNotContains(response, reverse("indigo_admin_history"))
        self.assertNotContains(response, reverse("indigo_admin_pipeline_list"))
        self.assertContains(response, reverse("indigo_admin_sandbox_list"))

    def test_dashboard_still_loads_when_nothing_has_been_set_up(self):
        self._login("admin")
        # No types, records or sandboxes at all
        response = self.client.get(reverse("indigo_admin_index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["waiting_total"], 0)

    def test_the_top_bar_shows_the_title_who_you_are_and_logout(self):
        self._login("admin")
        content = self.client.get(reverse("indigo_admin_index")).content.decode()
        self.assertIn('class="site-header__title"', content)
        self.assertIn('class="site-header__user"', content)
        user_bar = content[content.index('class="site-header__user"') :]
        # (the user's name opens a menu, which ends with Logout)
        user_bar = user_bar[: user_bar.index("</div>\n</div>")]
        self.assertIn("admin", user_bar)
        self.assertIn(reverse("logout"), user_bar)


class AdminToModerateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="1234")
        self.admin.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        self.newEvent = jsondataferret.pythonapi.newevent.newEvent
        self.NewEventData = jsondataferret.pythonapi.newevent.NewEventData

    def _record(self, type_id, public_id, name):
        type, _ = jsondataferret.models.Type.objects.get_or_create(
            public_id=type_id, defaults={"title": type_id}
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id=public_id
        )
        self.newEvent(
            [self.NewEventData(type, record, {"name": {"value": name}}, approved=True)]
        )
        return type, record

    def _edit(self, type, record, name, user=None):
        self.newEvent(
            [self.NewEventData(type, record, {"name": {"value": name}})], user=user
        )

    def test_lists_only_what_is_waiting_oldest_first_with_who_and_how_many(self):
        alice = User.objects.create_user(username="alice", password="1234")
        project_type, project_1 = self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ1", "One")
        _, project_2 = self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ2", "Two")
        fund_type, fund = self._record(TYPE_FUND_PUBLIC_ID, "FUND1", "A fund")
        # PROJ2 has waited longest; PROJ1 has two edits waiting
        self._edit(project_type, project_2, "Two (edited)", user=alice)
        self._edit(project_type, project_1, "One (edited)", user=self.admin)
        self._edit(project_type, project_1, "One (edited again)", user=alice)
        self._edit(fund_type, fund, "A fund (edited)", user=self.admin)

        response = self.client.get(reverse("indigo_admin_to_moderate"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 3)
        sections = {s["title"]: s["rows"] for s in response.context["sections"]}
        self.assertEqual(
            [r["record"].public_id for r in sections["Projects"]], ["PROJ2", "PROJ1"]
        )
        self.assertEqual([r["edit_count"] for r in sections["Projects"]], [1, 2])
        self.assertEqual(sections["Projects"][1]["latest_user"], alice)
        self.assertEqual(sections["Projects"][0]["name"], "Two")
        self.assertEqual(len(sections["Funds"]), 1)
        self.assertEqual(sections["Organisations"], [])
        # Each row links to review it, and the empty types are only mentioned in a line
        self.assertContains(
            response,
            reverse("indigo_admin_project_moderate", kwargs={"public_id": "PROJ2"}),
        )
        self.assertContains(
            response,
            reverse("indigo_admin_fund_moderate", kwargs={"public_id": "FUND1"}),
        )
        self.assertContains(response, "Nothing waiting for: Organisations, Pipelines")
        self.assertNotContains(response, 'id="moderate-organisation"')

    def test_a_record_stops_being_listed_once_its_edits_are_moderated(self):
        type, record = self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ1", "One")
        self._edit(type, record, "One (edited)")
        self.assertEqual(
            self.client.get(reverse("indigo_admin_to_moderate")).context["total"], 1
        )
        edit = jsondataferret.models.Edit.objects.get(
            record=record, approval_event=None
        )
        self.newEvent(
            [jsondataferret.pythonapi.newevent.NewEventRejection(edit)], user=self.admin
        )
        response = self.client.get(reverse("indigo_admin_to_moderate"))
        self.assertEqual(response.context["total"], 0)
        self.assertContains(response, "Nothing is waiting to be moderated")

    def test_it_loads_when_nothing_has_been_set_up(self):
        response = self.client.get(reverse("indigo_admin_to_moderate"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nothing is waiting to be moderated")

    def test_only_admins_can_see_it(self):
        self.client.logout()
        steward = User.objects.create_user(username="steward", password="1234")
        steward.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="indigo", codename="data_steward"
            )
        )
        self.client.login(username="steward", password="1234")
        self.assertIn(
            self.client.get(reverse("indigo_admin_to_moderate")).status_code, (302, 403)
        )
        self.client.logout()
        self.assertEqual(
            self.client.get(reverse("indigo_admin_to_moderate")).status_code, 302
        )


class AdminListRowsAndNewPageTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")

    def test_list_rows_have_a_small_edit_button_and_a_linked_name_but_no_view_button(
        self,
    ):
        Project.objects.create(
            public_id="INDIGO-POJ-0001", data_private={"name": {"value": "Alpha"}}
        )
        Organisation.objects.create(
            public_id="INDIGO-ORG-0001", data_private={"name": {"value": "Alpha"}}
        )
        for type_id, public_id in [
            (TYPE_FUND_PUBLIC_ID, "INDIGO-FUND-0001"),
            (TYPE_PIPELINE_PUBLIC_ID, "INDIGO-PL-0001"),
            (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "INDIGO-ARES-0001"),
            (TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID, "INDIGO-JUI-0001"),
        ]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id, cached_data={"name": {"value": "Alpha"}}
            )
        for name, public_id in [
            ("project", "INDIGO-POJ-0001"),
            ("organisation", "INDIGO-ORG-0001"),
            ("fund", "INDIGO-FUND-0001"),
            ("pipeline", "INDIGO-PL-0001"),
            ("assessment_resource", "INDIGO-ARES-0001"),
            ("joining_up_initiative", "INDIGO-JUI-0001"),
        ]:
            content = self.client.get(
                reverse(f"indigo_admin_{name}_list")
            ).content.decode()
            index = reverse(
                f"indigo_admin_{name}_index", kwargs={"public_id": public_id}
            )
            edit = reverse(f"indigo_admin_{name}_edit", kwargs={"public_id": public_id})
            self.assertNotIn(">View</a>", content, name)
            self.assertIn(
                f'href="{edit}" class="btn btn-primary btn-sm">Edit</a>', content, name
            )
            # Both the ID and the name take you to the record
            self.assertIn(f'<a href="{index}">{public_id}</a>', content, name)
            self.assertIn(
                f'<a href="{index}" class="text-body">Alpha</a>', content, name
            )

    def test_the_page_for_adding_a_record_by_name(self):
        for type_id in [
            TYPE_PROJECT_PUBLIC_ID,
            TYPE_ORGANISATION_PUBLIC_ID,
            TYPE_FUND_PUBLIC_ID,
            TYPE_PIPELINE_PUBLIC_ID,
            TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
        ]:
            jsondataferret.models.Type.objects.create(public_id=type_id, title=type_id)
        for name, noun in [
            ("project", "project"),
            ("organisation", "organisation"),
            ("fund", "fund"),
            ("pipeline", "pipeline"),
            ("assessment_resource", "assessment resource"),
        ]:
            url = reverse(f"indigo_admin_{name}_new")
            response = self.client.get(url)
            self.assertContains(response, f"Add {noun}", msg_prefix=name)
            self.assertContains(response, "Create and continue", msg_prefix=name)
            # The name box is ready to type in, and the history note is filled in
            self.assertContains(response, "autofocus", msg_prefix=name)
            self.assertContains(response, 'class="form-control"', msg_prefix=name)
            self.assertContains(response, "\nCreated</textarea>", msg_prefix=name)
            self.assertContains(
                response,
                f'href="{reverse(f"indigo_admin_{name}_list")}"',
                msg_prefix=name,
            )

    def test_adding_without_a_name_shows_what_is_wrong(self):
        jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        response = self.client.post(
            reverse("indigo_admin_fund_new"), {"name": "", "comment": "Created"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")
        self.assertFalse(Fund.objects.exists())

    def test_the_joining_up_page_has_a_cancel_link(self):
        response = self.client.get(reverse("indigo_admin_joining_up_initiative_new"))
        self.assertContains(response, "Add Joining Up Initiative")
        self.assertContains(
            response, f'href="{reverse("indigo_admin_joining_up_initiative_list")}"'
        )


class AdminModeratePageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="1234")
        self.admin.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        self.newEvent = jsondataferret.pythonapi.newevent.newEvent
        self.NewEventData = jsondataferret.pythonapi.newevent.NewEventData

    def _record(self, type_id, public_id):
        type = jsondataferret.models.Type.objects.create(
            public_id=type_id, title=type_id
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id=public_id
        )
        self.newEvent(
            [
                self.NewEventData(
                    type,
                    record,
                    {
                        "name": {"value": "Old name"},
                        "service_and_beneficiaries": {
                            "target_population": {"value": "Same population"}
                        },
                        "dates": {"notes": "Old dates note"},
                    },
                    approved=True,
                )
            ]
        )
        record.refresh_from_db()
        return type, record

    def _big_edit(self, type, record, comment="Tidying up", user=None):
        # Sends the whole record, as the web form does: one change, one new field, one removal, one repeat
        self.newEvent(
            [
                self.NewEventData(
                    type,
                    record,
                    {
                        "name": {"value": "New name"},
                        "service_and_beneficiaries": {
                            "target_population": {"value": "Same population"}
                        },
                        "dates": {"notes": None},
                        "stage_development": {"value": "Planning"},
                    },
                    mode=jsondataferret.EVENT_MODE_MERGE,
                )
            ],
            user=user,
            comment=comment,
        )

    def test_only_what_changes_is_shown_with_current_and_proposed_values(self):
        for type_id, public_id, name in [
            (TYPE_PROJECT_PUBLIC_ID, "PROJ1", "project"),
            (TYPE_FUND_PUBLIC_ID, "FUND1", "fund"),
        ]:
            type, record = self._record(type_id, public_id)
            self._big_edit(type, record, user=self.admin)
            response = self.client.get(
                reverse(
                    f"indigo_admin_{name}_moderate", kwargs={"public_id": public_id}
                )
            )
            self.assertEqual(response.status_code, 200, name)
            edit = response.context["edits"][0]
            changes = {c["kind"]: c for c in edit.changes}
            self.assertEqual(changes["changed"]["old"], "Old name", name)
            self.assertEqual(changes["changed"]["new"], "New name", name)
            self.assertEqual(changes["removed"]["old"], "Old dates note", name)
            self.assertIsNone(changes["removed"]["new"], name)
            self.assertEqual(changes["added"]["new"], "Planning", name)
            # The repeated field is not a change, so it is not listed
            self.assertEqual(len(edit.changes), 3, name)
            self.assertNotContains(response, "Same population", msg_prefix=name)
            self.assertContains(response, "Old name", msg_prefix=name)
            self.assertContains(response, "New name", msg_prefix=name)
            self.assertContains(response, "Tidying up", msg_prefix=name)
            self.assertContains(response, "3 changes", msg_prefix=name)
            # The kind of change has its own column
            self.assertContains(response, "<th>Change</th>", msg_prefix=name)
            for badge in ["New", "Changed", "Removed"]:
                self.assertContains(response, f">{badge}</span></td>", msg_prefix=name)

    def test_admins_can_decide_and_get_told_what_was_saved(self):
        type, record = self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ1")
        self._big_edit(type, record)
        url = reverse("indigo_admin_project_moderate", kwargs={"public_id": "PROJ1"})
        page = self.client.get(url)
        edit = page.context["edits"][0]
        self.assertContains(page, f'name="action_{edit.id}"', count=3)
        self.assertContains(page, "Save decisions")
        self.assertContains(page, 'name="comment"')
        # One edit, so no "all edits" shortcuts
        self.assertNotContains(page, "data-moderate-all=")

        response = self.client.post(
            url, {f"action_{edit.id}": "approve", "comment": "Looks good"}, follow=True
        )
        self.assertContains(response, "Moderation saved: 1 approved.")
        record.refresh_from_db()
        self.assertEqual(record.cached_data["name"]["value"], "New name")

    def test_rejecting_is_reported_and_leaves_the_record_alone(self):
        type, record = self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ1")
        self._big_edit(type, record)
        edit = jsondataferret.models.Edit.objects.get(
            record=record, approval_event=None
        )
        response = self.client.post(
            reverse("indigo_admin_project_moderate", kwargs={"public_id": "PROJ1"}),
            {f"action_{edit.id}": "reject", "comment": "No"},
            follow=True,
        )
        self.assertContains(response, "Moderation saved: 1 rejected.")
        record.refresh_from_db()
        self.assertEqual(record.cached_data["name"]["value"], "Old name")

    def test_several_edits_get_all_edits_shortcuts(self):
        type, record = self._record(TYPE_FUND_PUBLIC_ID, "FUND1")
        self._big_edit(type, record)
        self._big_edit(type, record, comment="Again")
        page = self.client.get(
            reverse("indigo_admin_fund_moderate", kwargs={"public_id": "FUND1"})
        )
        self.assertContains(page, "<strong>2</strong> edits waiting")
        self.assertContains(page, "data-moderate-all=", count=3)

    def test_data_stewards_can_look_but_not_decide(self):
        type, record = self._record(TYPE_FUND_PUBLIC_ID, "FUND1")
        self._big_edit(type, record)
        self.client.logout()
        steward = User.objects.create_user(username="steward", password="1234")
        steward.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="indigo", codename="data_steward"
            )
        )
        self.client.login(username="steward", password="1234")
        page = self.client.get(
            reverse("indigo_admin_fund_moderate", kwargs={"public_id": "FUND1"})
        )
        self.assertContains(page, "Old name")
        self.assertContains(page, "Only admins can approve or reject")
        self.assertNotContains(page, 'type="radio"')
        self.assertNotContains(page, "Save decisions")

    def test_nothing_waiting_says_so(self):
        self._record(TYPE_PROJECT_PUBLIC_ID, "PROJ1")
        self._record(TYPE_FUND_PUBLIC_ID, "FUND1")
        for name, public_id in [("project", "PROJ1"), ("fund", "FUND1")]:
            page = self.client.get(
                reverse(
                    f"indigo_admin_{name}_moderate", kwargs={"public_id": public_id}
                )
            )
            self.assertContains(
                page, "There is nothing to moderate here", msg_prefix=name
            )
            self.assertNotContains(page, "Save decisions", msg_prefix=name)

    def test_a_brand_new_record_shows_everything_as_new(self):
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id="FUND1"
        )
        self.newEvent(
            [self.NewEventData(type, record, {"name": {"value": "Brand new"}})]
        )
        page = self.client.get(
            reverse("indigo_admin_fund_moderate", kwargs={"public_id": "FUND1"})
        )
        self.assertEqual(
            [c["kind"] for c in page.context["edits"][0].changes], ["added"]
        )
        self.assertContains(page, "Brand new")


class AdminEditPageConsistencyTests(TestCase):
    TYPES = [
        (TYPE_PROJECT_PUBLIC_ID, "PROJ1", "project", "Project"),
        (TYPE_ORGANISATION_PUBLIC_ID, "ORG1", "organisation", "Organisation"),
        (TYPE_FUND_PUBLIC_ID, "FUND1", "fund", "Fund"),
        (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "pipeline", "Pipeline"),
        (
            TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
            "ARES1",
            "assessment_resource",
            "Assessment Resource",
        ),
        (
            TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
            "JUI1",
            "joining_up_initiative",
            "Joining Up Initiative",
        ),
    ]
    # The same box on both pages. The edit page also marks it as required (an asterisk and the required attribute), so
    # these are the parts the two have in common.
    COMMENT_BOX_START = (
        '<div class="form-group comment-box">\n'
        '    <label for="id_comment" class="comment-box__label">Comment for history'
    )
    COMMENT_TEXTAREA = (
        '<textarea name="comment" id="id_comment" class="form-control" rows="3"'
    )

    def setUp(self):
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        for type_id, public_id, name, title in self.TYPES:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            record = jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id
            )
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type, record, {"name": {"value": "Alpha"}}, approved=True
                    )
                ]
            )
            # Something to moderate
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type, record, {"name": {"value": "Beta"}}
                    )
                ]
            )

    def test_every_edit_page_is_laid_out_the_same_way(self):
        for type_id, public_id, name, title in self.TYPES:
            kwargs = {"public_id": public_id}
            response = self.client.get(
                reverse(f"indigo_admin_{name}_edit", kwargs=kwargs)
            )
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(
                response,
                f'<h2 class="record-header__title">Edit {title}: {public_id} Alpha</h2>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                "Changes will not be available until they have been moderated.",
                msg_prefix=name,
            )
            self.assertContains(response, self.COMMENT_BOX_START, msg_prefix=name)
            self.assertContains(response, self.COMMENT_TEXTAREA, msg_prefix=name)
            self.assertContains(response, ">Save changes</button>", msg_prefix=name)
            # Cancel goes back to the record, and the breadcrumbs go through its list
            record_url = reverse(f"indigo_admin_{name}_index", kwargs=kwargs)
            self.assertContains(
                response,
                f'<a href="{record_url}" class="btn btn-link">Cancel</a>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                f'<li class="breadcrumb-item"><a href="{reverse(f"indigo_admin_{name}_list")}">',
                msg_prefix=name,
            )

    def test_the_comment_and_buttons_are_in_a_footer_under_the_form_fields(self):
        for type_id, public_id, name, title in self.TYPES:
            content = self.client.get(
                reverse(f"indigo_admin_{name}_edit", kwargs={"public_id": public_id})
            ).content.decode()
            form_fields = content.index('class="rjsf-holder"')
            footer = content.index('<div class="edit-footer">')
            self.assertLess(form_fields, footer, name)
            # The comment box and both buttons are inside the footer, which ends the form
            footer_html = content[footer : content.index("</form>", footer)]
            self.assertIn('class="form-group comment-box"', footer_html, name)
            self.assertIn(">Save changes</button>", footer_html, name)
            self.assertIn(">Cancel</a>", footer_html, name)

    def test_the_comment_box_is_the_same_on_the_edit_and_moderation_pages(self):
        for type_id, public_id, name, title in self.TYPES:
            kwargs = {"public_id": public_id}
            edit = self.client.get(reverse(f"indigo_admin_{name}_edit", kwargs=kwargs))
            moderate = self.client.get(
                reverse(f"indigo_admin_{name}_moderate", kwargs=kwargs)
            )
            for page in [edit, moderate]:
                self.assertContains(page, self.COMMENT_BOX_START, msg_prefix=name)
                self.assertContains(page, self.COMMENT_TEXTAREA, msg_prefix=name)
                # The help text is under the label and above the box, like the help text of the fields
                content = page.content.decode()
                self.assertLess(
                    content.index('class="comment-box__label"'),
                    content.index('class="comment-box__help"'),
                    name,
                )
                self.assertLess(
                    content.index('class="comment-box__help"'),
                    content.index(self.COMMENT_TEXTAREA),
                    name,
                )
            # And the headings name the record the same way: "Edit Fund: ...", "Moderate Fund: ..."
            self.assertContains(
                moderate,
                f'<h2 class="record-header__title">Moderate {title}: {public_id} ',
                msg_prefix=name,
            )

    def test_what_you_wrote_is_kept_when_a_save_is_refused(self):
        response = self.client.post(
            reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ1"}),
            {"data": json.dumps({"name": "just text"}), "comment": "My reason"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This could not be saved:")
        self.assertContains(response, "name: &#x27;just text&#x27; is not of type")
        self.assertContains(response, ">My reason</textarea>")
        self.assertFalse(
            jsondataferret.models.Edit.objects.filter(
                record__public_id="PROJ1", approval_event=None, data__name="just text"
            ).exists()
        )

    def test_the_comment_is_still_saved_with_the_edit(self):
        response = self.client.post(
            reverse("indigo_admin_fund_edit", kwargs={"public_id": "FUND1"}),
            {"data": json.dumps({"name": {"value": "Gamma"}}), "comment": "Renamed it"},
        )
        self.assertEqual(response.status_code, 302)
        edit = jsondataferret.models.Edit.objects.filter(
            record__public_id="FUND1", approval_event=None
        ).latest("id")
        self.assertEqual(edit.creation_event.comment, "Renamed it")


class AdminHistoryPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin", password="1234")
        self.admin.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        self.url = reverse("indigo_admin_history")
        self.type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )

    def _event(self, comment, when, user=None, record_id="FUND1"):
        record, _ = jsondataferret.models.Record.objects.get_or_create(
            type=self.type, public_id=record_id
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    self.type, record, {"name": {"value": comment}}, approved=True
                )
            ],
            user=user,
            comment=comment,
        )
        event = jsondataferret.models.Event.objects.get(comment=comment)
        jsondataferret.models.Event.objects.filter(pk=event.pk).update(
            created=timezone.make_aware(when)
        )
        return event

    def _comments(self, params=None):
        response = self.client.get(self.url, params or {})
        self.assertEqual(response.status_code, 200)
        return [e.comment for e in response.context["page_obj"]]

    def test_both_ends_of_the_date_range_are_included(self):
        self._event("before", datetime.datetime(2026, 9, 30, 23, 59))
        self._event("first day", datetime.datetime(2026, 10, 1, 0, 30))
        self._event("last day", datetime.datetime(2026, 10, 12, 23, 30))
        self._event("after", datetime.datetime(2026, 10, 13, 0, 30))
        self.assertEqual(
            self._comments({"created__gt": "2026-10-01", "created__lt": "2026-10-12"}),
            ["last day", "first day"],
        )
        # Either end on its own
        self.assertEqual(
            self._comments({"created__gt": "2026-10-12"}), ["after", "last day"]
        )
        self.assertEqual(
            self._comments({"created__lt": "2026-10-01"}), ["first day", "before"]
        )
        self.assertEqual(len(self._comments()), 4)

    def test_the_filter_says_from_and_to_and_clear_only_shows_when_filtering(self):
        page = self.client.get(self.url)
        self.assertContains(page, ">From</label>")
        self.assertContains(page, ">To</label>")
        self.assertNotContains(page, "Created gt")
        self.assertNotContains(page, ">Clear</a>")
        filtered = self.client.get(self.url, {"created__gt": "2026-10-01"})
        self.assertContains(
            filtered, f'href="{self.url}" class="btn btn-secondary ml-2">Clear</a>'
        )
        # The date you chose is still in its box
        self.assertContains(filtered, 'value="2026-10-01"')

    def test_quick_ranges_filter_to_today_and_recent_days(self):
        today = timezone.localdate()
        page = self.client.get(self.url)
        for label, days_back in [
            ("Today", 0),
            ("Last 7 days", 6),
            ("Last 30 days", 29),
        ]:
            query = urllib.parse.urlencode(
                {
                    "created__gt": (
                        today - datetime.timedelta(days=days_back)
                    ).isoformat(),
                    "created__lt": today.isoformat(),
                }
            )
            link = f'href="{self.url}?{query}"'.replace("&", "&amp;")
            self.assertContains(page, link, msg_prefix=label)
            self.assertContains(page, f">{label}</a>")

    def test_a_quick_range_finds_todays_events(self):
        self._event("now", timezone.localtime().replace(tzinfo=None))
        self._event("last year", datetime.datetime(2020, 1, 1, 12, 0))
        today = timezone.localdate().isoformat()
        self.assertEqual(
            self._comments({"created__gt": today, "created__lt": today}), ["now"]
        )

    def test_records_link_to_their_admin_pages(self):
        self._event("changed", datetime.datetime(2026, 10, 1, 12, 0))
        page = self.client.get(self.url)
        fund = reverse("indigo_admin_fund_index", kwargs={"public_id": "FUND1"})
        self.assertContains(page, f'<a href="{fund}">Fund: FUND1</a>')

    def test_rows_are_easy_to_read(self):
        self._event(
            "by someone", datetime.datetime(2026, 10, 12, 16, 21), user=self.admin
        )
        self._event("by nobody", datetime.datetime(2026, 10, 12, 9, 5))
        page = self.client.get(self.url)
        self.assertContains(page, "12 Oct 2026, 16:21")
        self.assertContains(page, '<td class="text-nowrap">admin</td>')
        # No user is a dash, not the word None
        self.assertContains(page, '<td class="text-nowrap">&mdash;</td>')
        self.assertNotContains(page, ">None<")
        # The button says what it opens, and is the small size
        self.assertContains(page, 'class="btn btn-primary btn-sm">View change</a>')

    def test_it_says_how_many_events_there_are(self):
        self._event("one", datetime.datetime(2026, 10, 1, 12, 0))
        self.assertContains(self.client.get(self.url), "<strong>1</strong> event")
        self._event("two", datetime.datetime(2026, 10, 2, 12, 0))
        self.assertContains(self.client.get(self.url), "<strong>2</strong> events")

    def test_a_range_with_nothing_in_it_says_so_and_a_bad_date_does_not_break_it(self):
        self._event("one", datetime.datetime(2026, 10, 1, 12, 0))
        page = self.client.get(self.url, {"created__gt": "2030-01-01"})
        self.assertContains(page, "No events in that date range.")
        bad = self.client.get(self.url, {"created__gt": "banana"})
        self.assertEqual(bad.status_code, 200)
        self.assertContains(bad, "From:")

    def test_paging_keeps_the_date_range(self):
        for i in range(120):
            self._event(
                f"e{i}",
                datetime.datetime(2026, 10, 1, 12, 0) + datetime.timedelta(seconds=i),
            )
        page = self.client.get(self.url, {"created__gt": "2026-10-01"})
        self.assertContains(page, "Page 1 of 2")
        self.assertContains(page, "?created__gt=2026-10-01&amp;page=2")


class RecordSubpageTests(TestCase):
    """The history and change status pages of every type share templates; they must render for each type."""

    def test_history_and_change_status_pages_render_for_every_type(self):
        user = User.objects.create_user("sub-admin", password="pw")
        user.user_permissions.add(
            Permission.objects.get(codename="admin", content_type__app_label="indigo")
        )
        self.client.force_login(user)
        for type_id, public_id, label in [
            (TYPE_PROJECT_PUBLIC_ID, "PROJ1", "Project"),
            (TYPE_ORGANISATION_PUBLIC_ID, "ORG1", "Organisation"),
            (TYPE_FUND_PUBLIC_ID, "FUND1", "Fund"),
            (TYPE_PIPELINE_PUBLIC_ID, "PIPE1", "Pipeline"),
            (TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID, "ARES1", "Assessment Resource"),
            (TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID, "JUI1", "Joining Up Initiative"),
        ]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            record = jsondataferret.models.Record.objects.create(
                type=type, public_id=public_id
            )
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type, record, {"name": {"value": "Nm"}}, approved=True
                    )
                ],
                comment="c",
            )
            pages = ["history", "change_status", "moderate"]
            if type_id in (TYPE_PROJECT_PUBLIC_ID, TYPE_PIPELINE_PUBLIC_ID):
                pages.append("data_quality_report")
            if type_id != TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID:
                pages.append("import_form")
            for page in pages:
                response = self.client.get(
                    reverse(
                        f"indigo_admin_{type_id}_{page}",
                        kwargs={"public_id": public_id},
                    )
                )
                self.assertContains(response, f"{label} {public_id}", msg_prefix=page)

    def test_import_page_shows_form_errors_and_the_record_in_the_breadcrumbs(self):
        user = User.objects.create_user("imp-admin", password="pw")
        user.user_permissions.add(
            Permission.objects.get(codename="admin", content_type__app_label="indigo")
        )
        self.client.force_login(user)
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id="FUND1"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type, record, {"name": {"value": "Nm"}}, approved=True
                )
            ],
            comment="c",
        )
        url = reverse("indigo_admin_fund_import_form", kwargs={"public_id": "FUND1"})
        response = self.client.get(url)
        self.assertContains(response, 'href="/app/admin/fund/FUND1"')
        self.assertContains(response, "Comment for history")
        response = self.client.post(url, {})
        self.assertContains(response, "This field is required")

    def test_related_record_pages_render(self):
        user = User.objects.create_user("rel-admin", password="pw")
        user.user_permissions.add(
            Permission.objects.get(codename="admin", content_type__app_label="indigo")
        )
        self.client.force_login(user)
        for type_id, public_id, page, label in [
            (TYPE_ORGANISATION_PUBLIC_ID, "ORG1", "organisation_projects", "Projects"),
            (
                TYPE_ORGANISATION_PUBLIC_ID,
                "ORG1",
                "organisation_pipelines",
                "Pipelines",
            ),
            (TYPE_FUND_PUBLIC_ID, "FUND1", "fund_projects", "Projects"),
        ]:
            type = jsondataferret.models.Type.objects.get_or_create(
                public_id=type_id, defaults={"title": type_id}
            )[0]
            record = jsondataferret.models.Record.objects.get_or_create(
                type=type, public_id=public_id
            )[0]
            if record.cached_exists is False:
                jsondataferret.pythonapi.newevent.newEvent(
                    [
                        jsondataferret.pythonapi.newevent.NewEventData(
                            type, record, {"name": {"value": "Nm"}}, approved=True
                        )
                    ],
                    comment="c",
                )
            response = self.client.get(
                reverse(f"indigo_admin_{page}", kwargs={"public_id": public_id})
            )
            self.assertContains(response, label, msg_prefix=page)
            self.assertContains(response, f"{public_id}", msg_prefix=page)

    def test_restyled_admin_pages_render(self):
        user = User.objects.create_user("misc-admin", password="pw")
        user.user_permissions.add(
            Permission.objects.get(codename="admin", content_type__app_label="indigo")
        )
        self.client.force_login(user)
        type = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        record = jsondataferret.models.Record.objects.create(
            type=type, public_id="PROJ1"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type, record, {"name": {"value": "Nm"}}, approved=True
                )
            ],
            comment="c",
        )
        for name, kwargs, text in [
            (
                "indigo_admin_project_admin_users",
                {"public_id": "PROJ1"},
                "Data Stewards",
            ),
            ("indigo_admin_sandbox_list", {}, "Sandboxes"),
            (
                "indigo_admin_all_projects_data_quality_report",
                {},
                "Data Quality Report",
            ),
        ]:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertContains(response, text, msg_prefix=name)
