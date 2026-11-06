import html
import json
import re
from io import StringIO

import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from indigo import schemacheck
from indigo.forms import ProjectEditForm
from indigo.views_admin.common import edit_changes

SCHEMA = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "name": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
        },
        "amount": {"type": "number"},
        "kind": {"enum": ["senior", "junior"]},
        "status": {"type": "string", "enum": ["PUBLIC", "PRIVATE", "DISPUTED"]},
        "code": {"type": "string", "pattern": "^[0-9]+$"},
        "items": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "qty": {"type": "number"},
                    "status": {"type": "string", "enum": ["PUBLIC", "PRIVATE"]},
                },
            },
        },
    },
}


def _check(value, rules=None, type_id="thing"):
    value = {"id": "X", **value}
    result = schemacheck.check(SCHEMA, value, type_id, rules)
    blocking = {(p.path, p.rule) for p in result.blocking}
    warnings = {(p.path, p.rule) for p in result.warnings}
    return blocking, warnings


class ClassifyingProblemsTests(SimpleTestCase):
    def test_a_valid_record_has_no_problems(self):
        self.assertEqual(
            _check({"name": {"value": "A"}, "amount": 3, "kind": "senior"}),
            (set(), set()),
        )

    def test_a_number_where_text_is_expected_is_ignored(self):
        # Spreadsheet cells give numbers; it is harmless, so it is not even mentioned
        self.assertEqual(_check({"name": {"value": 5}}), (set(), set()))
        self.assertEqual(_check({"code": 123}), (set(), set()))

    def test_text_where_a_number_is_expected_is_a_warning(self):
        self.assertEqual(_check({"amount": "TBD"}), (set(), {("/amount", "type")}))

    def test_a_value_not_in_the_options_or_the_pattern_is_a_warning(self):
        self.assertEqual(
            _check({"kind": "Senior ", "code": "12a"}),
            (set(), {("/kind", "enum"), ("/code", "pattern")}),
        )

    def test_too_few_list_items_is_a_warning_and_the_path_has_the_position(self):
        self.assertEqual(
            _check({"items": [], "amount": 1}), (set(), {("/items", "minItems")})
        )
        self.assertEqual(
            _check({"items": [{"qty": "lots"}]}), (set(), {("/items/0/qty", "type")})
        )

    def test_the_wrong_shape_of_data_still_blocks(self):
        # A single value where a group is expected, or a list where a value is expected
        blocking, warnings = _check({"name": "just text", "amount": [1, 2]})
        self.assertEqual(blocking, {("/name", "type"), ("/amount", "type")})
        self.assertEqual(warnings, set())
        self.assertEqual(_check({"items": {"a": 1}})[0], {("/items", "type")})

    def test_a_missing_required_field_blocks_and_names_the_field(self):
        result = schemacheck.check(SCHEMA, {}, "thing")
        self.assertEqual(
            [(p.path, p.message) for p in result.blocking],
            [("/id", "This field is required")],
        )

    def test_strict_rules_block_everything(self):
        blocking, warnings = _check(
            {"name": {"value": 5}, "amount": "TBD", "kind": "x", "items": []},
            rules=schemacheck.STRICT_RULES,
        )
        self.assertEqual(
            blocking,
            {
                ("/name/value", "type"),
                ("/amount", "type"),
                ("/kind", "enum"),
                ("/items", "minItems"),
            },
        )
        self.assertEqual(warnings, set())


class StatusAndValuesTests(SimpleTestCase):
    def test_a_status_that_is_not_one_of_the_options_always_blocks(self):
        # Status decides what is shown publicly, so a mistyped one must not be saved
        self.assertEqual(_check({"status": "Pub"}), ({("/status", "enum")}, set()))
        self.assertEqual(
            _check({"items": [{"label": "a", "status": "HIDDEN"}]}),
            ({("/items/0/status", "enum")}, set()),
        )
        # ... while the same sort of mistake in another list of options only warns
        self.assertEqual(_check({"kind": "Senior"}), (set(), {("/kind", "enum")}))

    def test_a_problem_says_which_value_it_is_about(self):
        result = schemacheck.check(
            SCHEMA, {"id": "X", "amount": "TBD", "kind": "x", "items": []}, "thing"
        )
        self.assertEqual(
            [(p.path, p.value) for p in result.warnings],
            [("/amount", "TBD"), ("/items", []), ("/kind", "x")],
        )

    def test_double_star_matches_any_depth(self):
        parts = ["a", "b", "status"]
        self.assertTrue(schemacheck._matches("**/status", parts))
        self.assertTrue(schemacheck._matches("**/status", ["status"]))
        self.assertTrue(schemacheck._matches("/a/**/status", parts))
        self.assertFalse(schemacheck._matches("**/status", ["a", "statuses"]))
        self.assertFalse(schemacheck._matches("**/status", ["status", "a"]))
        self.assertFalse(schemacheck._matches("/a/b", parts))

    def test_a_type_can_relax_the_status_rule_for_itself(self):
        rules = json.loads(json.dumps(schemacheck.load_rules()))
        rules["types"] = {
            "thing": {
                "overrides": [{"path": "/status", "rule": "enum", "mode": "warn"}]
            }
        }
        self.assertEqual(
            _check({"status": "Pub"}, rules), (set(), {("/status", "enum")})
        )


class OverridesTests(SimpleTestCase):
    def _rules(self, overrides, type_id="thing"):
        rules = json.loads(json.dumps(schemacheck.load_rules()))
        rules["types"] = {type_id: {"overrides": overrides}}
        return rules

    def test_an_override_can_block_one_field(self):
        rules = self._rules([{"path": "/amount", "rule": "type", "mode": "block"}])
        self.assertEqual(
            _check({"amount": "TBD"}, rules), ({("/amount", "type")}, set())
        )

    def test_an_override_can_ignore_one_rule_and_list_positions_match_a_star(self):
        rules = self._rules(
            [{"path": "/items/*/qty", "rule": "type", "mode": "ignore"}]
        )
        self.assertEqual(
            _check({"items": [{"qty": "a"}, {"label": "b", "qty": "c"}]}, rules),
            (set(), set()),
        )

    def test_an_override_for_one_type_does_not_apply_to_another(self):
        rules = self._rules(
            [{"path": "/kind", "rule": "enum", "mode": "block"}], type_id="other"
        )
        self.assertEqual(
            _check({"kind": "x"}, rules, type_id="thing"), (set(), {("/kind", "enum")})
        )
        self.assertEqual(
            _check({"kind": "x"}, rules, type_id="other"), ({("/kind", "enum")}, set())
        )

    def test_the_first_matching_override_wins_and_a_star_rule_matches_any_keyword(self):
        rules = self._rules(
            [
                {"path": "/kind", "mode": "ignore"},
                {"path": "/kind", "rule": "enum", "mode": "block"},
            ]
        )
        self.assertEqual(_check({"kind": "x"}, rules), (set(), set()))


class PruneBlanksTests(SimpleTestCase):
    """The same as the tests of prune() in frontend/src/utils.test.js"""

    def test_blanks_and_the_empty_objects_they_leave_are_removed(self):
        self.assertEqual(
            schemacheck.prune_blanks(
                {"a": "", "b": None, "c": "  ", "d": {"e": ""}, "f": 0, "g": "x"}
            ),
            {"f": 0, "g": "x"},
        )

    def test_blank_list_items_are_dropped_but_an_empty_list_is_kept(self):
        self.assertEqual(
            schemacheck.prune_blanks({"l": ["a", "", None, {}, {"x": ""}], "e": []}),
            {"l": ["a"], "e": []},
        )


def _admin():
    user = User.objects.create_user("schema-admin", password="pw")
    user.user_permissions.add(
        Permission.objects.get(codename="admin", content_type__app_label="indigo")
    )
    return user


def _project(public_id="PROJ1", data=None):
    type = jsondataferret.models.Type.objects.get_or_create(
        public_id="project", defaults={"title": "Project"}
    )[0]
    record = jsondataferret.models.Record.objects.create(type=type, public_id=public_id)
    jsondataferret.pythonapi.newevent.newEvent(
        [
            jsondataferret.pythonapi.newevent.NewEventData(
                type, record, data or {"name": {"value": "Name"}}, approved=True
            )
        ],
        comment="c",
    )
    return record


class FormWarningsTests(TestCase):
    def test_a_form_with_only_warnings_is_valid_and_lists_them(self):
        data = {
            "name": {"value": "A"},
            "outcome_payment_commitments": [
                {"total_outcome_payments": {"amount": {"value": "TBD"}}}
            ],
        }
        form = ProjectEditForm({"data": json.dumps(data), "comment": "c"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            [(p.path, p.rule) for p in form.schema_warnings],
            [
                (
                    "/outcome_payment_commitments/0/total_outcome_payments/amount/value",
                    "type",
                )
            ],
        )

    def test_a_form_with_a_blocking_problem_is_not_valid(self):
        form = ProjectEditForm(
            {"data": json.dumps({"name": "just text"}), "comment": "c"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("/name", str(form.errors))


class EditSaveWithWarningsTests(TestCase):
    def setUp(self):
        _project()
        self.client.force_login(_admin())
        self.url = reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ1"})

    def test_a_save_with_warnings_goes_ahead_and_says_what_does_not_match(self):
        data = {
            "name": {"value": "Renamed"},
            "investments": [{"investment_type": {"value": "senior loan"}}],
        }
        response = self.client.post(
            self.url, {"data": json.dumps(data), "comment": "Warn"}, follow=True
        )
        self.assertContains(response, "Updates submitted")
        self.assertContains(
            response, "Saved, but 1 value does not match the data standard"
        )
        self.assertContains(response, "/investments/0/investment_type/value")
        self.assertTrue(
            jsondataferret.models.Edit.objects.filter(
                record__public_id="PROJ1", approval_event=None
            ).exists()
        )

    def test_a_clean_save_has_no_warning(self):
        response = self.client.post(
            self.url,
            {"data": json.dumps({"name": {"value": "Renamed"}}), "comment": "Clean"},
            follow=True,
        )
        self.assertContains(response, "Updates submitted")
        self.assertNotContains(response, "does not match the data standard")


def _record_of_type(type_id, public_id, data):
    type = jsondataferret.models.Type.objects.get_or_create(
        public_id=type_id, defaults={"title": type_id}
    )[0]
    record = jsondataferret.models.Record.objects.create(type=type, public_id=public_id)
    jsondataferret.pythonapi.newevent.newEvent(
        [
            jsondataferret.pythonapi.newevent.NewEventData(
                type, record, data, approved=True
            )
        ],
        comment="c",
    )
    return record


def _contains_a_blank(value):
    if isinstance(value, dict):
        return any(_contains_a_blank(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_a_blank(v) for v in value)
    return value is None or value == ""


# What spreadsheet uploads leave behind: a blank cell is stored as null
PIPELINE_WITH_STORED_BLANKS = {
    "name": {"value": "A pipeline"},
    "alternative_names": {"value": None},
    "notes": {"value": None},
    "dates": {"notes": None},
    "delivery_locations": [
        {
            "location_postcode": {"value": None},
            "lat_lng": {"lat": {"value": None}},
            "notes": None,
        }
    ],
    "misc7": {"proposed_financing_instruments": {"status": None}},
}


# The record as the database holds it: the form always sends these along too, so they are not "removed"
AS_STORED = {**PIPELINE_WITH_STORED_BLANKS, "id": "PIPE1", "organisations": []}


class SavingWithoutEditingTests(TestCase):
    """Saving a record you have not changed must not trip over the blanks that spreadsheet uploads stored as null."""

    def setUp(self):
        _record_of_type("pipeline", "PIPE1", PIPELINE_WITH_STORED_BLANKS)
        self.client.force_login(_admin())
        self.url = reverse("indigo_admin_pipeline_edit", kwargs={"public_id": "PIPE1"})

    def _data_in_the_form(self):
        page = self.client.get(self.url).content.decode()
        value = re.search(
            r'<input type="hidden" name="data"[^>]* value="([^"]*)"', page
        )
        return html.unescape(value.group(1))

    def test_the_form_starts_with_the_blanks_left_out(self):
        data = json.loads(self._data_in_the_form())
        self.assertFalse(_contains_a_blank(data), data)
        self.assertEqual(data["name"], {"value": "A pipeline"})

    def test_saving_what_the_form_started_with_works(self):
        response = self.client.post(
            self.url, {"data": self._data_in_the_form(), "comment": "No changes"}
        )
        self.assertEqual(response.status_code, 302)

    def test_data_with_the_blanks_still_in_is_accepted_too(self):
        # An old copy of the page, or anything else that sends the record as stored
        response = self.client.post(
            self.url,
            {"data": json.dumps(AS_STORED), "comment": "As stored"},
        )
        self.assertEqual(response.status_code, 302)

    def test_saving_it_untouched_shows_moderators_no_changes(self):
        self.client.post(
            self.url, {"data": self._data_in_the_form(), "comment": "None"}
        )
        edit = jsondataferret.models.Edit.objects.filter(
            record__public_id="PIPE1", approval_event=None
        ).latest("id")
        self.assertEqual(edit_changes(edit, edit.record), [])

    def test_a_real_problem_is_still_refused_among_the_blanks(self):
        data = {**AS_STORED, "name": "just text"}
        response = self.client.post(
            self.url, {"data": json.dumps(data), "comment": "Bad"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/name")
        self.assertNotContains(response, "None is not of type")


class WarningsReachTheFormTests(TestCase):
    def setUp(self):
        _project(
            "PROJ1",
            {
                "name": {"value": "Odd"},
                "investments": [{"investment_type": {"value": "senior loan"}}],
            },
        )
        self.client.force_login(_admin())
        self.url = reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ1"})

    def _warnings(self, response):
        html = response.content.decode()
        start = html.index('id="id_data_warnings"')
        start = html.index(">", start) + 1
        return json.loads(html[start : html.index("</script>", start)])

    def test_the_form_is_given_the_warnings_for_the_data_it_shows(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'data-warnings-id="id_data_warnings"')
        warnings = self._warnings(response)
        self.assertEqual(
            [(w["path"], w["value"]) for w in warnings],
            [("/investments/0/investment_type/value", "senior loan")],
        )

    def test_a_clean_record_has_none(self):
        _project("PROJ2", {"name": {"value": "Fine"}})
        url = reverse("indigo_admin_project_edit", kwargs={"public_id": "PROJ2"})
        self.assertEqual(self._warnings(self.client.get(url)), [])

    def test_a_refused_save_shows_the_warnings_for_what_was_submitted_too(self):
        data = {
            "name": "just text",
            "investments": [{"investment_type": {"value": "mezzanine"}}],
        }
        response = self.client.post(
            self.url, {"data": json.dumps(data), "comment": "c"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(w["path"], w["value"]) for w in self._warnings(response)],
            [("/investments/0/investment_type/value", "mezzanine")],
        )


class CheckRecordsCommandTests(TestCase):
    def setUp(self):
        _project("INDIGO-POJ-0001", {"name": {"value": "Fine"}})
        _project(
            "INDIGO-POJ-0002",
            {
                "name": {"value": "Odd"},
                "outcome_payment_commitments": [
                    {"total_outcome_payments": {"amount": {"value": "TBD"}}}
                ],
            },
        )

    def _run(self, *args):
        out = StringIO()
        call_command(
            "checkrecordsagainstschema", "--type", "project", *args, stdout=out
        )
        return out.getvalue()

    def test_relaxed_rules_save_the_odd_record_with_a_warning(self):
        output = self._run()
        self.assertIn("relaxed", output)
        self.assertIn(
            "project: 2 records. Refused: 0. Saved with warnings: 1. Clean: 1.", output
        )
        self.assertIn(
            "/outcome_payment_commitments/*/total_outcome_payments/amount/value", output
        )

    def test_strict_rules_refuse_it(self):
        output = self._run("--strict")
        self.assertIn("strict", output)
        self.assertIn("Refused: 1. Saved with warnings: 0. Clean: 1.", output)

    def test_a_type_that_is_not_set_up_is_an_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "checkrecordsagainstschema", "--type", "fund", stdout=StringIO()
            )
