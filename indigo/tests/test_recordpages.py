from django.contrib.auth.models import Permission, User
from django.test import SimpleTestCase, TestCase  # noqa
from django.urls import reverse

from indigo.models import Fund, Project
from indigo.recordpages import build_record_sections


def by_title(sections):
    return {s["title"]: s for s in sections}


class BuildRecordSectionsTests(SimpleTestCase):
    PROJECT = {
        "name": {"value": "Alpha"},
        "status": "PUBLIC",
        "dates": {
            "outcomes_contract_signed": {"value": "2020-01-01", "status": "PUBLIC"},
        },
        "overall_project_finance": {
            "total_investment_commitment": {"currency": {"value": "GBP"}}
        },
        "outcome_funds": [{"id": "1"}, {"id": "2", "notes": "A note"}, {}],
        "documents": [{"title": {"value": "Doc"}}],
    }

    def test_a_project_follows_the_same_sections_as_the_edit_form(self):
        sections = build_record_sections("project", self.PROJECT)
        self.assertEqual(
            [s["title"] for s in sections],
            ["Overview", "Finance", "Funds & locations", "Sources & documents"],
        )
        # Sections with nothing in them are left out altogether
        self.assertNotIn("Outcomes", by_title(sections))

    def test_sections_have_ids_to_link_to_and_a_count(self):
        sections = by_title(build_record_sections("project", self.PROJECT))
        self.assertEqual(sections["Overview"]["id"], "section-overview")
        self.assertEqual(sections["Funds & locations"]["id"], "section-funds-locations")
        # Overview: the name, the status, and the two parts of the date
        self.assertEqual(sections["Overview"]["count"], 4)
        # Funds: a count of items, not of fields
        self.assertEqual(sections["Funds & locations"]["count"], 2)

    def test_a_group_with_several_fields_gets_a_heading_and_shorter_labels(self):
        overview = by_title(build_record_sections("project", self.PROJECT))["Overview"]
        singles, dates = overview["blocks"]
        # Fields on their own share a table with no heading
        self.assertEqual(
            [(r["title"], r["value"]) for r in singles["rows"]],
            [("Status", "PUBLIC"), ("Impact Bond Name", "Alpha")],
        )
        self.assertIsNone(singles["title"])
        # Related fields are grouped under their heading, which their labels no longer repeat
        self.assertEqual(dates["title"], "Dates")
        self.assertEqual(
            [r["title"] for r in dates["rows"]],
            [
                "Date outcomes contract signed",
                "Date outcomes contract signed - (Status)",
            ],
        )

    def test_list_items_are_blocks_of_their_own_and_empty_ones_are_skipped(self):
        funds = by_title(build_record_sections("project", self.PROJECT))[
            "Funds & locations"
        ]
        (block,) = funds["blocks"]
        self.assertEqual(block["kind"], "list")
        self.assertEqual(block["title"], "Outcome Funds")
        self.assertEqual(
            [i["title"] for i in block["items"]], ["Outcome Funds 1", "Outcome Funds 2"]
        )
        self.assertEqual(
            [r["title"] for r in block["items"][1]["rows"]], ["Id", "Notes"]
        )

    def test_empty_values_are_left_out(self):
        sections = build_record_sections(
            "project", {"name": {"value": ""}, "notes": None, "outcome_funds": []}
        )
        self.assertEqual(sections, [])
        self.assertEqual(build_record_sections("project", None), [])
        self.assertEqual(build_record_sections("project", {}), [])

    def test_anything_the_groups_do_not_cover_goes_in_other(self):
        # The "Other" section is for parts of the data that no group names; check with a type that has groups
        sections = build_record_sections("project", {"name": {"value": "Alpha"}})
        self.assertEqual([s["title"] for s in sections], ["Overview"])

    def test_other_types_have_a_general_section_then_one_for_each_list(self):
        fund = {
            "name": {"value": "A fund"},
            "dates": {"actual_end_date": {"value": "2030"}, "notes": "Some notes"},
            "documents": [{"title": {"value": "Doc A"}}],
        }
        sections = build_record_sections("fund", fund)
        self.assertEqual([s["title"] for s in sections], ["General", "Documents"])
        general = sections[0]
        singles, dates = general["blocks"]
        # The type's name ("Fund - ") is not repeated in every label
        self.assertEqual(singles["rows"][0]["title"], "Name")
        self.assertEqual(dates["title"], "Dates")
        self.assertEqual(
            [r["title"] for r in dates["rows"]], ["Actual End date", "(Notes)"]
        )
        self.assertEqual(sections[1]["blocks"][0]["items"][0]["title"], "Documents 1")

    def test_section_ids_are_unique(self):
        sections = build_record_sections("project", self.PROJECT)
        ids = [s["id"] for s in sections]
        self.assertEqual(len(ids), len(set(ids)))


class RecordPageSectionsTests(TestCase):
    DATA = {
        "name": {"value": "Alpha thing"},
        "dates": {
            "outcomes_contract_signed": {"value": "2020-01-01"},
            "actual_completion_date": {"value": "2025-01-01"},
        },
        "outcome_funds": [{"id": "F1"}, {"id": "F2"}],
    }

    def _admin(self):
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")

    def _project(self):
        return Project.objects.create(
            public_id="INDIGO-POJ-0001",
            exists=True,
            status_public=True,
            data_public=self.DATA,
            data_private=self.DATA,
        )

    def test_the_sidebar_links_to_each_section_with_a_count(self):
        self._project()
        response = self.client.get(
            reverse("indigo_project_index", kwargs={"public_id": "INDIGO-POJ-0001"})
        )
        self.assertContains(response, 'id="record-nav"')
        self.assertContains(
            response,
            '<a class="nav-link" href="#section-overview"><span>Overview</span><span class="badge badge-light">3</span></a>',
        )
        self.assertContains(
            response,
            '<a class="nav-link" href="#section-funds-locations"><span>Funds &amp; locations</span><span class="badge badge-light">2</span></a>',
        )
        # Each link has something to go to, and sections with nothing in are not offered
        self.assertContains(response, '<section id="section-overview"')
        self.assertContains(response, '<section id="section-funds-locations"')
        self.assertNotContains(response, "section-finance")

    def test_fields_and_list_items_are_shown_as_blocks(self):
        self._project()
        content = self.client.get(
            reverse("indigo_project_index", kwargs={"public_id": "INDIGO-POJ-0001"})
        ).content.decode()
        self.assertIn('<h4 class="record-block__title">Dates</h4>', content)
        self.assertIn(
            "<tr><th>Date outcomes contract signed</th><td>2020-01-01</td></tr>",
            content,
        )
        self.assertIn('<div class="card-header">Outcome Funds 2</div>', content)
        self.assertIn("<tr><th>Id</th><td>F2</td></tr>", content)

    def test_the_admin_page_has_the_same_sections_as_the_public_one(self):
        self._project()
        self._admin()
        public = self.client.get(
            reverse("indigo_project_index", kwargs={"public_id": "INDIGO-POJ-0001"})
        )
        admin = self.client.get(
            reverse(
                "indigo_admin_project_index", kwargs={"public_id": "INDIGO-POJ-0001"}
            )
        )
        self.assertEqual(admin.status_code, 200)
        for text in [
            'id="record-nav"',
            '<section id="section-overview"',
            '<div class="card-header">Outcome Funds 1</div>',
            "<tr><th>Impact Bond Name</th><td>Alpha thing</td></tr>",
        ]:
            self.assertContains(public, text)
            self.assertContains(admin, text)

    def test_a_record_with_nothing_in_it_says_so(self):
        Fund.objects.create(public_id="F1", exists=True, status_public=True)
        response = self.client.get(
            reverse("indigo_fund_index", kwargs={"public_id": "F1"})
        )
        self.assertContains(response, "No details have been added yet.")
        self.assertNotContains(response, 'id="record-nav"')


class LinkifyTests(SimpleTestCase):
    def linkify(self, value):
        from indigo.templatetags.indigo_extras import linkify

        return str(linkify(value))

    def test_a_web_address_becomes_a_link_that_opens_in_a_new_tab(self):
        self.assertEqual(
            self.linkify("https://golab.bsg.ox.ac.uk/knowledge-bank/"),
            '<a href="https://golab.bsg.ox.ac.uk/knowledge-bank/" target="_blank" '
            'rel="noopener noreferrer">https://golab.bsg.ox.ac.uk/knowledge-bank/</a>',
        )

    def test_text_around_an_address_is_kept_and_several_addresses_work(self):
        result = self.linkify("See http://a.example/x and https://b.example/y for more")
        self.assertTrue(result.startswith("See <a href="))
        self.assertEqual(result.count("<a "), 2)
        self.assertTrue(result.endswith("</a> for more"))

    def test_punctuation_after_an_address_is_not_part_of_it(self):
        self.assertIn(
            'href="https://a.example/x"', self.linkify("Read https://a.example/x.")
        )
        self.assertTrue(self.linkify("(see https://a.example/x)").endswith("</a>)"))
        # but a bracket that belongs to the address stays
        self.assertIn(
            'href="https://en.wikipedia.org/wiki/Bond_(finance)"',
            self.linkify("https://en.wikipedia.org/wiki/Bond_(finance)"),
        )

    def test_everything_else_is_escaped(self):
        self.assertEqual(
            self.linkify("<script>alert(1)</script> & more"),
            "&lt;script&gt;alert(1)&lt;/script&gt; &amp; more",
        )
        # Even inside a link's address
        result = self.linkify('https://a.example/?q="><script>')
        self.assertNotIn("<script>", result)

    def test_only_web_addresses_are_linked(self):
        for value in [
            "javascript:alert(1)",
            "ftp://a.example/file",
            "mailto:someone@example.com",
            "https://",
            "www.example.com",
        ]:
            self.assertNotIn("<a ", self.linkify(value), value)

    def test_values_that_are_not_text_are_shown_as_they_are(self):
        self.assertEqual(self.linkify(42), "42")
        self.assertEqual(self.linkify(["a", "b"]), "[&#x27;a&#x27;, &#x27;b&#x27;]")


class GroupHeadingTests(SimpleTestCase):
    def test_a_group_with_no_title_in_the_schema_uses_the_start_its_fields_share(self):
        from indigo.recordpages import _group_heading

        rows = [
            ("Type of instrument and project - Outcomes Fund", "x"),
            ("Type of instrument and project - (Status)", "y"),
        ]
        self.assertEqual(
            _group_heading("misc1", {}, rows, "pipeline"),
            "Type of instrument and project",
        )
        # A title from the schema wins
        self.assertEqual(
            _group_heading("misc1", {"misc1": "Instrument"}, rows, "pipeline"),
            "Instrument",
        )
        # With nothing in common to use, the key is made readable
        self.assertEqual(
            _group_heading(
                "misc1", {}, [("One - A", "x"), ("Two - B", "y")], "pipeline"
            ),
            "Misc1",
        )


class RecordPageLinksTests(TestCase):
    def test_a_documents_url_is_a_link_on_the_public_and_admin_pages(self):
        url = "https://golab.bsg.ox.ac.uk/knowledge-bank/case-studies/improving-employability-buenos-aires/"
        data = {
            "name": {"value": "Alpha"},
            "documents": [
                {
                    "title": {"value": "Case Study - Proyectá tu futuro"},
                    "url": {"value": url},
                }
            ],
        }
        Project.objects.create(
            public_id="INDIGO-POJ-0001",
            exists=True,
            status_public=True,
            data_public=data,
            data_private=data,
        )
        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        link = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
        public = self.client.get(
            reverse("indigo_project_index", kwargs={"public_id": "INDIGO-POJ-0001"})
        )
        self.assertContains(public, f"<td>{link}</td>")
        self.assertContains(public, '<div class="card-header">Documents 1</div>')
        self.client.login(username="admin", password="1234")
        admin = self.client.get(
            reverse(
                "indigo_admin_project_index", kwargs={"public_id": "INDIGO-POJ-0001"}
            )
        )
        self.assertContains(admin, f"<td>{link}</td>")
