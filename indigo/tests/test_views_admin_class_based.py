"""The project and organisation admin pages are class based like the other types; check the parts that are special to them."""
import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.models import AdminUserHasPermissionsForProject, Project


def _user(username, codename):
    user = User.objects.create_user(username, password="pw")
    user.user_permissions.add(
        Permission.objects.get(codename=codename, content_type__app_label="indigo")
    )
    return user


def _record(type_public_id, public_id, name):
    type = jsondataferret.models.Type.objects.get_or_create(
        public_id=type_public_id, defaults={"title": type_public_id}
    )[0]
    record = jsondataferret.models.Record.objects.create(type=type, public_id=public_id)
    jsondataferret.pythonapi.newevent.newEvent(
        [
            jsondataferret.pythonapi.newevent.NewEventData(
                type, record, {"name": {"value": name}}, approved=True
            )
        ],
        comment="c",
    )
    return record


class AdminProjectClassBasedTests(TestCase):
    def test_a_steward_who_adds_a_project_can_see_it_but_not_other_projects(self):
        _record(TYPE_PROJECT_PUBLIC_ID, "INDIGO-POJ-0900", "Someone else's")
        steward = _user("steward", "data_steward")
        self.client.force_login(steward)
        response = self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        self.assertEqual(response.status_code, 302)
        mine = Project.objects.exclude(public_id="INDIGO-POJ-0900").get()
        self.assertTrue(
            AdminUserHasPermissionsForProject.objects.get(
                user=steward, project=mine
            ).permission_access
        )
        for page in ["index", "history", "moderate"]:
            url = reverse(
                f"indigo_admin_project_{page}", kwargs={"public_id": mine.public_id}
            )
            self.assertEqual(self.client.get(url).status_code, 200, page)
            url = reverse(
                f"indigo_admin_project_{page}", kwargs={"public_id": "INDIGO-POJ-0900"}
            )
            self.assertEqual(self.client.get(url).status_code, 403, page)

    def test_an_admin_adding_a_project_does_not_give_anyone_access(self):
        self.client.force_login(_user("admin", "admin"))
        self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        self.assertEqual(AdminUserHasPermissionsForProject.objects.count(), 0)

    def test_a_steward_only_lists_their_own_projects(self):
        _record(TYPE_PROJECT_PUBLIC_ID, "INDIGO-POJ-0900", "Someone else's")
        steward = _user("steward", "data_steward")
        self.client.force_login(steward)
        self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        response = self.client.get(reverse("indigo_admin_project_list"))
        self.assertEqual(
            [p.public_id for p in response.context["items"]],
            [Project.objects.exclude(public_id="INDIGO-POJ-0900").get().public_id],
        )


@override_settings(
    FILE_UPLOAD_HANDLERS=["django.core.files.uploadhandler.TemporaryFileUploadHandler"]
)
class AdminOrganisationClassBasedTests(TestCase):
    def setUp(self):
        _record(TYPE_ORGANISATION_PUBLIC_ID, "INDIGO-ORG-0900", "Acme")
        self.client.force_login(_user("admin", "admin"))

    def test_blank_form_and_filled_form_download_as_spreadsheets(self):
        for name, kwargs in [
            ("indigo_admin_organisation_download_blank_form", {}),
            (
                "indigo_admin_organisation_download_form",
                {"public_id": "INDIGO-ORG-0900"},
            ),
        ]:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response["Content-Type"], "application/vnd.ms-excel")
            self.assertEqual(response.content[:2], b"PK", name)

    def test_a_downloaded_form_can_be_uploaded_again(self):
        form = self.client.get(
            reverse(
                "indigo_admin_organisation_download_form",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            )
        ).content
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse(
                "indigo_admin_organisation_import_form",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            ),
            {
                "file": SimpleUploadedFile("organisation.xlsx", form),
                "comment": "round trip",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse(
                "indigo_admin_organisation_index",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            ),
        )

    def test_the_search_page_and_list_are_the_same_page(self):
        for name in [
            "indigo_admin_organisation_list",
            "indigo_admin_organisation_search",
        ]:
            response = self.client.get(reverse(name), {"search": "Acme"})
            self.assertEqual(
                [o.public_id for o in response.context["items"]],
                ["INDIGO-ORG-0900"],
                name,
            )
            self.assertContains(response, "Go to ID", msg_prefix=name)


class ProjectDataQualityReportIndexTests(TestCase):
    def test_it_summarises_priorities_and_groups_the_fields_by_section(self):
        self.client.force_login(_user("dq-admin", "admin"))
        Project.objects.create(
            public_id="INDIGO-POJ-0001",
            exists=True,
            status_public=True,
            data_quality_report_counts_by_priority={"0": 2, "1": 5},
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0002",
            exists=True,
            data_quality_report_counts_by_priority={"1": 1},
        )
        response = self.client.get(
            reverse("indigo_admin_all_projects_data_quality_report")
        )
        by_priority = {r["priority"]: r for r in response.context["priority_summary"]}
        self.assertEqual((by_priority[0]["projects"], by_priority[0]["issues"]), (1, 2))
        self.assertEqual((by_priority[1]["projects"], by_priority[1]["issues"]), (2, 6))
        self.assertEqual((by_priority[3]["projects"], by_priority[3]["issues"]), (0, 0))
        self.assertEqual(response.context["count_projects"], 2)
        self.assertEqual(response.context["count_public_projects"], 1)
        titles = [s["title"] for s in response.context["sections"]]
        self.assertIn("Overview", titles)
        self.assertEqual(len(titles), len(set(titles)))
        # Every field there are statistics for is linked to, once, with its key safely encoded
        links = [f["url"] for s in response.context["sections"] for f in s["fields"]]
        self.assertEqual(len(links), len(set(links)))
        self.assertTrue(any(l.endswith("?field=%2Fname%2Fvalue") for l in links))
        self.assertContains(response, 'id="dq-filter"')


class ProjectDataQualityReportFieldPagesTests(TestCase):
    def setUp(self):
        self.client.force_login(_user("dq-admin", "admin"))
        Project.objects.create(
            public_id="INDIGO-POJ-0001",
            exists=True,
            status_public=True,
            data_public={
                "name": {"value": "Has a name"},
                "outcome_funds": [{"id": "F"}],
            },
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0002",
            exists=True,
            status_public=True,
            data_public={"name": {"value": ""}, "outcome_funds": []},
        )
        Project.objects.create(
            public_id="INDIGO-POJ-0003",
            exists=True,
            status_public=True,
            data_public={"name": {"value": "Another"}},
        )
        # Private projects are not counted
        Project.objects.create(
            public_id="INDIGO-POJ-0004",
            exists=True,
            data_public={"name": {"value": "Private"}},
        )

    def test_a_single_field_shows_how_many_projects_have_a_value(self):
        response = self.client.get(
            reverse("indigo_admin_all_projects_data_quality_report_field_single"),
            {"field": "/name/value"},
        )
        self.assertEqual(
            (
                response.context["with_value"],
                response.context["without_value"],
                response.context["total"],
                response.context["percent_with_value"],
            ),
            (2, 1, 3, 67),
        )
        self.assertContains(response, "67%")
        self.assertContains(response, "2 of 3")
        self.assertNotContains(response, "plotly")

    def test_a_list_field_counts_projects_with_at_least_one_item(self):
        response = self.client.get(
            reverse("indigo_admin_all_projects_data_quality_report_field_list"),
            {"field": "/outcome_funds"},
        )
        self.assertEqual(
            (response.context["with_value"], response.context["total"]), (1, 3)
        )
        self.assertContains(response, "at least one item")

    def test_an_unknown_field_is_a_404_and_no_projects_is_not_an_error(self):
        url = reverse("indigo_admin_all_projects_data_quality_report_field_single")
        self.assertEqual(self.client.get(url, {"field": "/nope"}).status_code, 404)
        Project.objects.update(status_public=False)
        response = self.client.get(url, {"field": "/name/value"})
        self.assertContains(response, "no public projects yet")


class ProjectsByPriorityPageTests(TestCase):
    def test_it_is_split_into_pages_with_the_worst_projects_first(self):
        self.client.force_login(_user("pri-admin", "admin"))
        for n in range(1, 111):
            Project.objects.create(
                public_id=f"INDIGO-POJ-{n:04d}",
                exists=True,
                data_private={"name": {"value": f"Project {n}"}},
                data_quality_report_counts_by_priority={"1": n % 7 + 1},
            )
        # No problems at this level, so it is not listed
        Project.objects.create(
            public_id="INDIGO-POJ-0999",
            exists=True,
            data_quality_report_counts_by_priority={"2": 4},
        )
        url = reverse(
            "indigo_admin_all_projects_data_quality_list_projects_by_priority_highest",
            kwargs={"priority": 1},
        )
        first = self.client.get(url)
        rows = list(first.context["page_obj"])
        self.assertEqual(len(rows), 100)
        self.assertEqual(first.context["page_obj"].paginator.count, 110)
        counts = [row["count"] for row in rows]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(counts[0], 7)
        self.assertContains(first, "Page 1 of 2")
        self.assertContains(first, "Missing: the most important fields")
        second = self.client.get(url, {"page": 2})
        self.assertEqual(len(second.context["page_obj"]), 10)
        self.assertNotContains(first, "INDIGO-POJ-0999")
        self.assertNotContains(second, "INDIGO-POJ-0999")
        self.assertContains(first, "Project ")

    def test_a_level_with_no_problems_and_a_bad_level(self):
        self.client.force_login(_user("pri-admin", "admin"))
        name = (
            "indigo_admin_all_projects_data_quality_list_projects_by_priority_highest"
        )
        self.assertContains(
            self.client.get(reverse(name, kwargs={"priority": 0})),
            "No projects have any errors at this level",
        )
        self.assertEqual(
            self.client.get(reverse(name, kwargs={"priority": 7})).status_code, 404
        )


class AdminThemeTests(TestCase):
    """The admin's teal colours are scoped to the admin pages' main area, so the public pages keep Bootstrap's blue."""

    def test_only_the_admin_pages_have_the_admin_theme(self):
        self.client.force_login(_user("theme-admin", "admin"))
        self.assertContains(
            self.client.get(reverse("indigo_admin_index")),
            'class="content container admin-main"',
        )
        self.assertNotContains(self.client.get(reverse("indigo_index")), "admin-main")
        self.assertNotContains(
            self.client.get(reverse("indigo_project_list")), "admin-main"
        )
