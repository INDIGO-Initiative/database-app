from django.test import TestCase  # noqa

from indigo.models import Sandbox
from indigo.updatedata import filter_values


class UpdateDataFilterValues(TestCase):
    def test_key_public(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": "PUBLIC"},
        }

        out = filter_values(input, keys_with_own_status_subfield=["/name"])

        assert {"name": {"value": "Project With Ferrets", "status": None},} == out

    def test_key_not_public(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": ""},
        }

        out = filter_values(input, keys_with_own_status_subfield=["/name"])

        assert {"name": None} == out

    def test_key_in_correct_sandbox(self):

        sandbox = Sandbox()
        sandbox.public_id = "s1"

        input = {
            "name": {
                "value": "Project With Ferrets",
                "status": "SANDBOX",
                "sandboxes": "s1, s2",
            },
        }

        out = filter_values(
            input, keys_with_own_status_subfield=["/name"], sandbox=sandbox
        )

        assert {
            "name": {
                "value": "Project With Ferrets",
                "status": None,
                "sandboxes": None,
            },
        } == out

    def test_key_in_wrong_sandbox(self):

        sandbox = Sandbox()
        sandbox.public_id = "s1"

        input = {
            "name": {
                "value": "Project With Ferrets",
                "status": "SANDBOX",
                "sandboxes": "s3475",
            },
        }

        out = filter_values(
            input, keys_with_own_status_subfield=["/name"], sandbox=sandbox
        )

        assert {"name": None,} == out

    def test_list_item_public(self):

        input = {"alt_names": [{"value": "Project With Ferrets", "status": "PUBLIC"},]}

        out = filter_values(
            input, lists_with_items_with_own_status_subfield=["/alt_names"]
        )

        assert {"alt_names": [{"value": "Project With Ferrets"},]} == out

    def test_list_item_not_public(self):

        input = {"alt_names": [{"value": "Project With Ferrets", "status": ""},]}

        out = filter_values(
            input, lists_with_items_with_own_status_subfield=["/alt_names"]
        )

        assert {"alt_names": []} == out

    def test_list_item_public_in_correct_sandbox(self):

        sandbox = Sandbox()
        sandbox.public_id = "s1"

        input = {
            "alt_names": [
                {
                    "value": "Project With Ferrets",
                    "status": "SANDBOX",
                    "sandboxes": "s1, s2",
                },
            ]
        }

        out = filter_values(
            input,
            lists_with_items_with_own_status_subfield=["/alt_names"],
            sandbox=sandbox,
        )

        assert {"alt_names": [{"value": "Project With Ferrets"},]} == out

    def test_list_item_public_in_wrong_sandbox(self):

        sandbox = Sandbox()
        sandbox.public_id = "s1"

        input = {
            "alt_names": [
                {
                    "value": "Project With Ferrets",
                    "status": "SANDBOX",
                    "sandboxes": "s7697679",
                },
            ]
        }

        out = filter_values(
            input,
            lists_with_items_with_own_status_subfield=["/alt_names"],
            sandbox=sandbox,
        )

        assert {"alt_names": []} == out

    def test_list_items_order_preserved(self):

        sandbox = Sandbox()
        sandbox.public_id = "s1"

        input = {
            "alt_names": [
                {"value": "Project With Ferrets", "status": "PUBLIC"},
                {"value": "Bob's Free-range Ferrets", "status": "PRIVATE"},
                {
                    "value": "Linda's Ferret Sanctuary",
                    "status": "SANDBOX",
                    "sandboxes": "s1, s2",
                },
                {
                    "value": "Jeff's Ferret Zoo",
                    "status": "SANDBOX",
                    "sandboxes": "s76486",
                },
            ]
        }

        out = filter_values(
            input,
            lists_with_items_with_own_status_subfield=["/alt_names"],
            sandbox=sandbox,
        )

        assert {
            "alt_names": [
                {"value": "Project With Ferrets",},
                {"value": "Linda's Ferret Sanctuary"},
            ]
        } == out
