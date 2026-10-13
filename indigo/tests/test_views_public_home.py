from django.contrib.auth.models import Permission, User
from django.test import TestCase  # noqa
from django.urls import reverse

from indigo.models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    Project,
)


class PublicHomePageTests(TestCase):
    def _login(self, codename=None):
        user = User.objects.create_user(username=codename or "plain", password="1234")
        if codename:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="indigo", codename=codename
                )
            )
        self.client.login(username=user.username, password="1234")

    def test_shows_a_card_for_each_kind_of_public_data(self):
        response = self.client.get(reverse("indigo_index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [s["title"] for s in response.context["sections"]],
            [
                "Projects",
                "Organisations",
                "Funds",
                "Pipelines",
                "Assessment Resources",
                "Joining Up Initiatives",
            ],
        )
        for section in response.context["sections"]:
            self.assertContains(response, reverse(section["list_url"]))
            self.assertContains(response, reverse(section["api_url"]))

    def test_counts_only_what_is_public(self):
        Project.objects.create(public_id="P1", exists=True, status_public=True)
        Project.objects.create(public_id="P2", exists=True, status_public=True)
        Project.objects.create(public_id="P3", exists=True, status_public=False)
        Project.objects.create(public_id="P4", exists=False, status_public=True)
        Organisation.objects.create(public_id="O1", exists=True, status_public=True)
        Fund.objects.create(public_id="F1", exists=True, status_public=False)
        counts = {
            s["title"]: s["count"]
            for s in self.client.get(reverse("indigo_index")).context["sections"]
        }
        self.assertEqual(counts["Projects"], 2)
        self.assertEqual(counts["Organisations"], 1)
        self.assertEqual(counts["Funds"], 0)
        self.assertEqual(counts["Pipelines"], 0)

    def test_describes_and_links_the_downloads(self):
        response = self.client.get(reverse("indigo_index"))
        for url_name in [
            "indigo_all_public_data_file_per_record_in_zip",
            "indigo_all_public_data_file_per_data_type_csv_in_zip",
            "indigo_all_public_data_sqlite",
        ]:
            self.assertContains(response, reverse(url_name))
        self.assertContains(response, "SQLite database")

    def test_visitors_are_offered_login_and_not_admin(self):
        response = self.client.get(reverse("indigo_index"))
        self.assertContains(response, reverse("login"))
        self.assertNotContains(response, reverse("indigo_admin_index"))
        self.assertNotContains(response, reverse("logout"))

    def test_admins_and_data_stewards_are_offered_admin(self):
        for codename in ["admin", "data_steward"]:
            self.client.logout()
            self._login(codename)
            response = self.client.get(reverse("indigo_index"))
            self.assertContains(
                response, reverse("indigo_admin_index"), msg_prefix=codename
            )
            self.assertContains(response, reverse("logout"), msg_prefix=codename)

    def test_other_logged_in_users_are_not_offered_admin(self):
        self._login()
        response = self.client.get(reverse("indigo_index"))
        self.assertContains(response, reverse("logout"))
        self.assertNotContains(response, reverse("indigo_admin_index"))

    def test_other_public_pages_have_the_same_top_bar(self):
        response = self.client.get(reverse("indigo_project_list"))
        self.assertContains(response, 'class="site-header__title"')
        self.assertContains(response, 'class="site-header__user"')


class PublicListPageTests(TestCase):
    LISTS = [
        # list view, model, how the list's own page links to a record, the words used
        ("project", Project, "Projects"),
        ("organisation", Organisation, "Organisations"),
        ("fund", Fund, "Funds"),
        ("pipeline", Pipeline, "Pipelines"),
        ("assessment_resource", AssessmentResource, "Assessment Resources"),
        ("joining_up_initiative", JoiningUpInitiative, "Joining Up Initiatives"),
    ]

    def _public(self, model, public_id, name, **kwargs):
        return model.objects.create(
            public_id=public_id,
            exists=True,
            status_public=True,
            data_public={"name": {"value": name}},
            **kwargs,
        )

    def test_rows_link_through_the_id_and_name_and_have_no_buttons(self):
        for name, model, title in self.LISTS:
            self._public(model, "X1", "Alpha")
            response = self.client.get(reverse(f"indigo_{name}_list"))
            index = reverse(f"indigo_{name}_index", kwargs={"public_id": "X1"})
            # The ID stays on one line (it would otherwise wrap at its hyphens in a narrow column)
            self.assertContains(
                response,
                f'<td class="text-nowrap"><a href="{index}">X1</a></td>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                f'<a href="{index}" class="text-body">Alpha</a>',
                msg_prefix=name,
            )
            # Nothing to edit on the public site, and no View button as the row is a link
            self.assertNotContains(response, ">View</a>", msg_prefix=name)
            self.assertNotContains(response, ">Edit</a>", msg_prefix=name)
            self.assertNotContains(response, "Add ", msg_prefix=name)

    def test_only_public_records_are_listed(self):
        self._public(Project, "P1", "Visible")
        Project.objects.create(public_id="P2", exists=True, status_public=False)
        Project.objects.create(public_id="P3", exists=False, status_public=True)
        response = self.client.get(reverse("indigo_project_list"))
        self.assertEqual([p.public_id for p in response.context["projects"]], ["P1"])

    def test_search_finds_by_id_or_public_name(self):
        self._public(Project, "INDIGO-POJ-0001", "Peterborough Bond")
        self._public(Project, "INDIGO-POJ-0002", "Homeless Pathways")
        self._public(Project, "INDIGO-POJ-0013", "Other")
        url = reverse("indigo_project_list")

        def ids(search):
            return [
                p.public_id
                for p in self.client.get(url, {"search": search}).context["projects"]
            ]

        self.assertEqual(ids("peterborough"), ["INDIGO-POJ-0001"])
        self.assertEqual(ids("PATHWAYS"), ["INDIGO-POJ-0002"])
        self.assertEqual(ids("POJ-0013"), ["INDIGO-POJ-0013"])
        self.assertEqual(len(ids("")), 3)
        response = self.client.get(url, {"search": "zzz"})
        self.assertContains(response, "No projects match your search")
        self.assertContains(response, 'value="zzz"')
        self.assertContains(response, "Clear")

    def test_search_never_looks_at_private_data(self):
        Project.objects.create(
            public_id="P1",
            exists=True,
            status_public=True,
            data_public={"name": {"value": "Public name"}},
            data_private={
                "name": {"value": "Public name"},
                "alternative_names": {"value": "Secret codename"},
            },
        )
        response = self.client.get(reverse("indigo_project_list"), {"search": "secret"})
        self.assertEqual(len(response.context["projects"]), 0)
        self.assertNotContains(response, "Secret codename")

    def test_every_list_can_be_searched(self):
        for name, model, title in self.LISTS:
            self._public(model, "X1", "Alpha thing")
            self._public(model, "X2", "Beta thing")
            url = reverse(f"indigo_{name}_list")
            found = self.client.get(url, {"search": "alpha"}).context["items"]
            self.assertEqual([i.public_id for i in found], ["X1"], name)

    def test_long_lists_are_split_into_pages_and_keep_the_search(self):
        for i in range(120):
            self._public(Project, f"INDIGO-POJ-{i:04d}", f"Project {i}")
        url = reverse("indigo_project_list")
        first = self.client.get(url)
        self.assertEqual(len(first.context["projects"]), 100)
        self.assertContains(first, "Page 1 of 2")
        self.assertEqual(len(self.client.get(url, {"page": 2}).context["projects"]), 20)
        self.assertContains(
            self.client.get(url, {"search": "Project"}), "?search=Project&page=2"
        )
        self.assertContains(self.client.get(url, {"page": "banana"}), "Page 1 of 2")

    def test_download_menus(self):
        expected = {
            "project": [
                "indigo_project_list_download",
                "indigo_project_list_download_social_investment_prototype",
                "indigo_project_download_blank_form",
                "indigo_project_download_data_quality_report",
            ],
            "organisation": [
                "indigo_organisation_list_download",
                "indigo_organisation_download_blank_form",
            ],
            "fund": ["indigo_fund_list_download"],
            "pipeline": [
                "indigo_pipeline_list_download",
                "indigo_pipeline_public_data_file_per_record_in_zip",
                "indigo_pipeline_public_data_file_per_data_type_csv_in_zip",
            ],
            "assessment_resource": [],
            "joining_up_initiative": [],
        }
        for name, model, title in self.LISTS:
            self._public(model, "X1", "Alpha")
            content = self.client.get(reverse(f"indigo_{name}_list")).content.decode()
            if expected[name]:
                self.assertIn(
                    ">Download</button>".replace(">", ">", 1),
                    content.replace(
                        '<i class="fa-solid fa-download mr-1" aria-hidden="true"></i>',
                        "",
                    ),
                    name,
                )
                menu = content[content.index("dropdown-menu") : content.index("<table")]
                for url_name in expected[name]:
                    self.assertIn(reverse(url_name), menu, f"{name} {url_name}")
            else:
                self.assertNotIn("dropdown-menu", content, name)

    def test_lists_have_breadcrumbs_back_home(self):
        for name, model, title in self.LISTS:
            response = self.client.get(reverse(f"indigo_{name}_list"))
            self.assertContains(
                response,
                f'<li class="breadcrumb-item"><a href="{reverse("indigo_index")}">Home</a></li>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                f'<li class="breadcrumb-item active" aria-current="page">{title}</li>',
                msg_prefix=name,
            )

    def test_record_pages_have_breadcrumbs_through_their_list(self):
        for name, model, title in self.LISTS:
            self._public(model, "X1", "Alpha")
            response = self.client.get(
                reverse(f"indigo_{name}_index", kwargs={"public_id": "X1"})
            )
            self.assertEqual(response.status_code, 200, name)
            self.assertContains(
                response,
                f'<li class="breadcrumb-item"><a href="{reverse("indigo_index")}">Home</a></li>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                f'<li class="breadcrumb-item"><a href="{reverse(f"indigo_{name}_list")}">{title}</a></li>',
                msg_prefix=name,
            )
            self.assertContains(
                response,
                '<li class="breadcrumb-item active" aria-current="page">X1</li>',
                msg_prefix=name,
            )

    def test_the_home_page_has_no_breadcrumbs(self):
        self.assertNotContains(
            self.client.get(reverse("indigo_index")), "breadcrumb-item"
        )

    def test_lists_say_how_many_results_there_are(self):
        self._public(Project, "P1", "Alpha one")
        self._public(Project, "P2", "Alpha two")
        self._public(Project, "P3", "Beta")
        url = reverse("indigo_project_list")
        # Everything, then a search; one result is "result", not "results"
        self.assertContains(self.client.get(url), "<strong>3</strong> results")
        searched = self.client.get(url, {"search": "alpha"})
        self.assertContains(
            searched, "<strong>2</strong> results for &ldquo;alpha&rdquo;"
        )
        self.assertContains(
            self.client.get(url, {"search": "beta"}),
            "<strong>1</strong> result for &ldquo;beta&rdquo;",
        )
        # No count when there is nothing to count
        self.assertNotContains(self.client.get(url, {"search": "zzz"}), "list-count")

    def test_a_long_list_says_which_part_is_shown(self):
        for i in range(120):
            self._public(Project, f"INDIGO-POJ-{i:04d}", f"Project {i}")
        url = reverse("indigo_project_list")
        self.assertContains(
            self.client.get(url), "Showing 1&ndash;100 of <strong>120</strong> results"
        )
        self.assertContains(
            self.client.get(url, {"page": 2}),
            "Showing 101&ndash;120 of <strong>120</strong> results",
        )


class UrlLayoutTests(TestCase):
    """Other websites link to pages under /app/ (eg the download page on the Government Outcomes Lab site), so the layout
    of the site's addresses must not change without those links being kept working."""

    def test_the_public_home_page_is_at_app(self):
        self.assertEqual(reverse("indigo_index"), "/app/")
        response = self.client.get("/app/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Better data for better social outcomes")

    def test_the_root_of_the_site_sends_visitors_to_app(self):
        response = self.client.get("/", follow=True)
        self.assertEqual(response.redirect_chain[0][0], "/app")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Better data for better social outcomes")

    def test_public_pages_and_the_api_are_under_app(self):
        self.assertEqual(reverse("indigo_project_list"), "/app/project")
        self.assertEqual(
            reverse("indigo_project_index", kwargs={"public_id": "P1"}),
            "/app/project/P1",
        )
        self.assertEqual(reverse("indigo_api1_project_list"), "/app/api1/project")
        self.assertEqual(self.client.get("/app/project").status_code, 200)

    def test_the_application_admin_is_under_app_and_djangos_admin_is_at_admin(self):
        self.assertEqual(reverse("indigo_admin_index"), "/app/admin/")
        self.assertEqual(reverse("indigo_admin_project_list"), "/app/admin/project")
        self.assertEqual(reverse("admin:index"), "/admin/")
        self.assertContains(
            self.client.get("/admin/", follow=True), "Django administration"
        )

    def test_links_to_home_go_to_app(self):
        for url in ["/app/project", reverse("login")]:
            self.assertContains(self.client.get(url), 'href="/app/">', msg_prefix=url)


class PublicRecordPageTests(TestCase):
    # name of the type, its model, what a record is called, and whether it has a spreadsheet form to download
    TYPES = [
        ("project", Project, "Project", True),
        ("organisation", Organisation, "Organisation", True),
        ("fund", Fund, "Fund", True),
        ("pipeline", Pipeline, "Pipeline", True),
        ("assessment_resource", AssessmentResource, "Assessment Resource", False),
        ("joining_up_initiative", JoiningUpInitiative, "Joining Up Initiative", False),
    ]

    def _record(self, model, public_id="X1", **data):
        return model.objects.create(
            public_id=public_id,
            exists=True,
            status_public=True,
            data_public={"name": {"value": "Alpha thing"}, **data},
        )

    def test_the_heading_has_the_id_and_name(self):
        for name, model, title, _ in self.TYPES:
            self._record(model)
            response = self.client.get(
                reverse(f"indigo_{name}_index", kwargs={"public_id": "X1"})
            )
            self.assertContains(
                response,
                f'<h2 class="record-header__title">{title}: X1 Alpha thing</h2>',
                msg_prefix=name,
            )

    def test_every_record_has_a_download_menu_at_the_top(self):
        for name, model, title, has_form in self.TYPES:
            self._record(model)
            response = self.client.get(
                reverse(f"indigo_{name}_index", kwargs={"public_id": "X1"})
            )
            content = response.content.decode()
            menu = content[content.index("dropdown-menu") : content.index("<table")]
            json_url = reverse(f"indigo_api1_{name}_index", kwargs={"public_id": "X1"})
            self.assertIn(f'href="{json_url}">JSON data</a>', menu, name)
            self.assertIn(
                ">Download</button>",
                content.replace(
                    '<i class="fa-solid fa-download mr-1" aria-hidden="true"></i>', ""
                ),
                name,
            )
            form_url = f"/app/{name}/X1/download_form"
            if has_form:
                self.assertIn(f'href="{form_url}">Download Form</a>', menu, name)
            else:
                self.assertNotIn("Download Form", content, name)
            # The menu is at the top, and the old button under the table is gone
            self.assertNotIn('btn btn-primary">Download Form', content, name)

    def test_the_fields_are_in_a_table_with_tidy_titles(self):
        self._record(Project)
        response = self.client.get(
            reverse("indigo_project_index", kwargs={"public_id": "X1"})
        )
        self.assertContains(response, 'class="table record-details"')
        # The ID is in the heading, not repeated in the table
        self.assertNotContains(response, "<tr><th>ID</th>")
        # "Impact Bond Name - (Value)" reads better as "Impact Bond Name"
        self.assertContains(
            response, "<tr><th>Impact Bond Name</th><td>Alpha thing</td></tr>"
        )
        self.assertNotContains(response, "(Value)")

    def test_records_that_are_not_public_are_not_found(self):
        for name, model, title, _ in self.TYPES:
            model.objects.create(public_id="HIDDEN", exists=True, status_public=False)
            model.objects.create(public_id="GONE", exists=False, status_public=True)
            for public_id in ["HIDDEN", "GONE", "MISSING"]:
                response = self.client.get(
                    reverse(f"indigo_{name}_index", kwargs={"public_id": public_id})
                )
                self.assertEqual(response.status_code, 404, f"{name} {public_id}")

    def test_the_menu_links_work(self):
        self._record(Project)
        form = self.client.get("/app/project/X1/download_form")
        self.assertEqual(form.status_code, 200)
        api = self.client.get(
            reverse("indigo_api1_project_index", kwargs={"public_id": "X1"})
        )
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["project"]["id"], "X1")


class TidyFieldTitleTests(TestCase):
    def test_leaves_off_a_trailing_value_part_only(self):
        from indigo.utils import tidy_field_title

        self.assertEqual(
            tidy_field_title("Impact Bond Name - (Value)"), "Impact Bond Name"
        )
        self.assertEqual(tidy_field_title("Dates - (Notes)"), "Dates - (Notes)")
        self.assertEqual(
            tidy_field_title("Investments 2: Amount - (Value)"), "Investments 2: Amount"
        )
        self.assertEqual(
            tidy_field_title("A (Value) in the middle"), "A (Value) in the middle"
        )


class BreadcrumbBarColourTests(TestCase):
    def test_the_admin_breadcrumb_bar_is_marked_as_admin_and_the_public_one_is_not(
        self,
    ):
        user = User.objects.create_user(username="martin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        # Public pages have the plain bar
        public = self.client.get(reverse("indigo_project_list"))
        self.assertContains(public, '<div class="page-header breadcrumb-bar">')
        self.assertNotContains(public, "breadcrumb-bar--admin")
        # Admin pages have the teal one
        self.client.login(username="martin", password="1234")
        for url in [
            reverse("indigo_admin_index"),
            reverse("indigo_admin_project_list"),
            reverse("indigo_admin_to_moderate"),
        ]:
            self.assertContains(
                self.client.get(url),
                '<div class="page-header breadcrumb-bar breadcrumb-bar--admin">',
                msg_prefix=url,
            )


class LibraryPagesAreNotExposedTests(TestCase):
    def test_the_library_pages_are_gone(self):
        from django.urls import NoReverseMatch

        for name in [
            "jsondataferret_index",
            "jsondataferret_event_list",
            "jsondataferret_record_index",
            "jsondataferret_record_edit_json_schema",
        ]:
            with self.assertRaises(NoReverseMatch, msg=name):
                reverse(
                    name,
                    kwargs={"type_id": "x", "record_id": "y"}
                    if "record" in name
                    else None,
                )

    def test_old_links_go_to_the_admin_home_page(self):
        for old in [
            "/jsondataferret/",
            "/jsondataferret/event",
            "/jsondataferret/type/project/record/INDIGO-POJ-0001",
            "/jsondataferret/type/project/record/INDIGO-POJ-0001/edit_json_schema",
        ]:
            response = self.client.get(old)
            self.assertEqual(response.status_code, 302, old)
            self.assertEqual(response.url, reverse("indigo_admin_index"), old)

    def test_the_old_edit_form_cannot_be_posted_to_either(self):
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        response = self.client.post(
            "/jsondataferret/type/project/record/INDIGO-POJ-0001/edit_json_schema",
            {"data": "{}", "comment": "x"},
        )
        # Sent away, not handled
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("indigo_admin_index"))

    def test_the_django_admin_still_has_the_record_types(self):
        user = User.objects.create_superuser("root", "root@example.com", "1234")
        self.client.force_login(user)
        response = self.client.get("/admin/jsondataferret/type/")
        self.assertEqual(response.status_code, 200)


class SiteFooterTests(TestCase):
    NOTICE_START = "Important Notice and Disclaimer on INDIGO Data"

    def test_every_public_page_has_the_disclaimer_footer(self):
        Project.objects.create(
            public_id="P1",
            exists=True,
            status_public=True,
            data_public={"name": {"value": "Alpha"}},
        )
        for url in [
            reverse("indigo_index"),
            reverse("indigo_project_list"),
            reverse("indigo_project_index", kwargs={"public_id": "P1"}),
            reverse("login"),
        ]:
            response = self.client.get(url)
            self.assertContains(
                response, '<footer class="site-footer">', msg_prefix=url
            )
            self.assertContains(response, self.NOTICE_START, msg_prefix=url)

    def test_the_wording_is_the_agreed_text(self):
        content = self.client.get(reverse("indigo_index")).content.decode()
        for text in [
            "INDIGO data are shared for research and policy analysis purposes.",
            "These data are NOT shared for auditing, investment, or legal purposes.",
            "Please independently verify any data that you might use in decision making.",
            "We provide no guarantees or assurances as to the quality of these data.",
            "which may not have been included in a project’s budget.",
            "Help us improve our data quality: email us at",
            "Please also give input via the INDIGO Data Definitions Improvement Tool and INDIGO Feedback Questionnaire.",
        ]:
            self.assertIn(text, content)

    def test_the_email_address_is_a_link(self):
        self.assertContains(
            self.client.get(reverse("indigo_index")),
            '<a href="mailto:indigo@bsg.ox.ac.uk">indigo@bsg.ox.ac.uk</a>',
        )

    def test_the_admin_has_no_footer(self):
        user = User.objects.create_user(username="martin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="martin", password="1234")
        for url in [
            reverse("indigo_admin_index"),
            reverse("indigo_admin_project_list"),
        ]:
            self.assertNotContains(
                self.client.get(url), 'class="site-footer"', msg_prefix=url
            )

    def test_the_footer_goes_to_the_bottom_of_short_pages(self):
        self.assertContains(
            self.client.get(reverse("indigo_index")), '<body class="has-footer">'
        )


class SiteLogoTests(TestCase):
    LOGO = '<img src="/static/img/go-lab-logo.svg" alt="Government Outcomes Lab">'

    def test_the_footer_has_the_logo_linking_to_the_government_outcomes_lab(self):
        for url in [
            reverse("indigo_index"),
            reverse("indigo_project_list"),
            reverse("login"),
        ]:
            content = self.client.get(url).content.decode()
            footer = content[content.index('<footer class="site-footer">') :]
            self.assertIn(
                '<a href="https://golab.bsg.ox.ac.uk/" target="_blank" rel="noopener noreferrer" '
                f'title="Government Outcomes Lab website">{self.LOGO}</a>',
                footer,
                url,
            )

    def test_the_logo_is_only_in_the_footer_not_the_header(self):
        content = self.client.get(reverse("indigo_index")).content.decode()
        self.assertEqual(content.count("go-lab-logo"), 1)
        self.assertGreater(
            content.index("go-lab-logo"), content.index('<footer class="site-footer">')
        )

    def test_the_admin_has_neither_the_footer_nor_the_logo(self):
        user = User.objects.create_user(username="martin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="martin", password="1234")
        self.assertNotContains(
            self.client.get(reverse("indigo_admin_index")), "go-lab-logo"
        )

    def test_the_logo_file_is_a_complete_svg(self):
        import os
        import xml.etree.ElementTree as ET

        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "img",
            "go-lab-logo.svg",
        )
        root = ET.parse(path).getroot()  # (fails if the file is cut off part way)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertEqual(root.attrib["viewBox"], "0 0 211 45")

    def test_it_is_left_out_rather_than_broken_if_the_file_is_missing(self):
        from unittest import mock

        with mock.patch(
            "indigo.templatetags.indigo_extras.finders.find", return_value=None
        ):
            response = self.client.get(reverse("indigo_index"))
        self.assertNotContains(response, "site-footer__logo")
        self.assertContains(response, '<footer class="site-footer">')


class HomePageIntroTests(TestCase):
    def test_the_home_page_opens_with_the_intro(self):
        response = self.client.get(reverse("indigo_index"))
        self.assertContains(
            response,
            '<h2 class="home-intro__title">Better data for better social outcomes</h2>',
        )
        self.assertContains(
            response,
            "International Network for Data on Impact and Government Outcomes (INDIGO). "
            "Browse the records that have been made public, search them by name or ID, or download all of "
            "the data as spreadsheets, CSV files or a SQLite database.",
        )

    def test_the_intro_comes_before_the_datasets(self):
        content = self.client.get(reverse("indigo_index")).content.decode()
        self.assertLess(content.index("home-intro__title"), content.index("Browse"))


class SiteHeaderIconTests(TestCase):
    def _header(self, url):
        content = self.client.get(url).content.decode()
        return content[content.index('<h1 class="site-header__title">') :]

    def test_the_icon_is_left_of_the_site_title_on_public_pages(self):
        for url in [
            reverse("indigo_index"),
            reverse("indigo_project_list"),
            reverse("login"),
        ]:
            header = self._header(url)
            link_end = header.index("</h1>")
            title = header[:link_end]
            self.assertIn(
                '<svg class="site-header__icon" viewBox="0 0 68 90"', title, url
            )
            self.assertLess(title.index("<svg"), title.index("<span>"), url)
            # the title is still there, and the whole thing still goes to the home page
            self.assertIn(f'<a href="{reverse("indigo_index")}">', title, url)

    def test_the_admin_header_has_it_too(self):
        user = User.objects.create_user(username="martin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="martin", password="1234")
        header = self._header(reverse("indigo_admin_index"))
        self.assertIn('<svg class="site-header__icon"', header[: header.index("</h1>")])

    def test_the_icon_is_complete_and_takes_the_colour_of_the_text(self):
        header = self._header(reverse("indigo_index"))
        icon = header[header.index("<svg") : header.index("</svg>") + 6]
        # The whole outline is there (it starts and ends where the original does), drawn in the text colour
        self.assertIn('fill="currentColor"', icon)
        self.assertIn('d="M26.664 82.4084H1.71781', icon)
        self.assertTrue(
            icon.rstrip("</svg>").rstrip().endswith('Z"/>') or 'Z"/></svg>' in icon
        )
        self.assertGreater(len(icon), 1500)
        # It is decoration: the title next to it says what the site is
        self.assertIn('aria-hidden="true"', icon)


class UserMenuTests(TestCase):
    def _login(self, codename=None):
        user = User.objects.create_user(username=codename or "plain", password="1234")
        if codename:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="indigo", codename=codename
                )
            )
        self.client.login(username=user.username, password="1234")

    def _menu(self, url):
        content = self.client.get(url).content.decode()
        start = content.index('<div class="dropdown site-header__menu">')
        return content[start : content.index("</div>\n</div>", start) + 13]

    def test_the_name_opens_a_menu_with_admin_and_logout_on_public_pages(self):
        for codename in ["admin", "data_steward"]:
            self.client.logout()
            self._login(codename)
            menu = self._menu(reverse("indigo_index"))
            self.assertIn("dropdown-toggle", menu, codename)
            self.assertIn(codename, menu)  # the username
            self.assertIn(f'href="{reverse("indigo_admin_index")}"', menu, codename)
            self.assertIn(f'href="{reverse("logout")}"', menu, codename)
            # no separate Admin or Logout buttons any more
            content = self.client.get(reverse("indigo_index")).content.decode()
            self.assertEqual(content.count(f'href="{reverse("logout")}"'), 1, codename)
            self.assertEqual(
                content.count(f'href="{reverse("indigo_admin_index")}"'), 1, codename
            )

    def test_other_users_only_get_logout(self):
        self._login()
        menu = self._menu(reverse("indigo_index"))
        self.assertIn(f'href="{reverse("logout")}"', menu)
        self.assertNotIn(reverse("indigo_admin_index"), menu)

    def test_the_admin_menu_links_to_the_public_site_and_logout(self):
        self._login("admin")
        menu = self._menu(reverse("indigo_admin_index"))
        self.assertIn(f'href="{reverse("indigo_index")}"', menu)
        self.assertIn("Public site", menu)
        self.assertIn(f'href="{reverse("logout")}"', menu)
        self.assertNotIn("Admin</a>", menu)

    def test_visitors_still_get_a_login_button_and_no_menu(self):
        content = self.client.get(reverse("indigo_index")).content.decode()
        self.assertNotIn("site-header__menu", content)
        self.assertIn(
            f'href="{reverse("login")}" class="btn btn-sm btn-outline-light">Login</a>',
            content,
        )
