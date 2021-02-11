from django.test import TestCase  # noqa

from indigo.updatedata import get_sandbox_only_data


class UpdateDataGetSandBoxOnlyData(TestCase):
    def test_key_public(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": "PUBLIC"},
            "alt_names": {"value": "Cool", "status": ""},
        }

        out = get_sandbox_only_data(input, keys_with_own_status_subfield=["/name"])

        assert {} == out

    def test_key_sandbox(self):

        input = {
            "name": {
                "value": "Project With Ferrets",
                "status": "SANDBOX",
                "sandboxes": "sandbox1",
            },
            "alt_names": {"value": "Cool", "status": ""},
        }

        out = get_sandbox_only_data(input, keys_with_own_status_subfield=["/name"])

        assert {
            "sandbox1": {
                "name": {
                    "value": "Project With Ferrets",
                    "status": None,
                    "sandboxes": None,
                }
            }
        } == out

    def test_list_public(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": ""},
            "alt_names": [{"value": "Cool", "status": "PUBLIC"},],
        }

        out = get_sandbox_only_data(
            input, lists_with_items_with_own_status_subfield=["/alt_names"]
        )

        assert {} == out

    def test_list_sandbox(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": ""},
            "alt_names": [
                {"value": "Cool", "status": "SANDBOX", "sandboxes": "sandbox1"},
            ],
        }

        out = get_sandbox_only_data(
            input, lists_with_items_with_own_status_subfield=["/alt_names"]
        )

        assert {"sandbox1": {"alt_names": [{"value": "Cool"}]}} == out

    def test_list_sandbox_complex(self):

        input = {
            "name": {"value": "Project With Ferrets", "status": ""},
            "alt_names": [
                {"value": "Cool", "status": "SANDBOX", "sandboxes": "sandbox1"},
            ],
            "organisations": [
                {
                    "value": "Linda's Ferret Sanctuary",
                    "status": "SANDBOX",
                    "sandboxes": "sandbox1",
                },
                {
                    "value": "Bob's Free-range Ferrets",
                    "status": "SANDBOX",
                    "sandboxes": "sandbox2",
                },
                {
                    "value": "Jeff's Ferret Zoo",
                    "status": "SANDBOX",
                    "sandboxes": "sandbox2, sandbox3",
                },
            ],
        }

        out = get_sandbox_only_data(
            input,
            lists_with_items_with_own_status_subfield=["/alt_names", "/organisations"],
        )

        assert {
            "sandbox1": {
                "alt_names": [{"value": "Cool"}],
                "organisations": [{"value": "Linda's Ferret Sanctuary"}],
            },
            "sandbox2": {
                "organisations": [
                    {"value": "Bob's Free-range Ferrets"},
                    {"value": "Jeff's Ferret Zoo"},
                ]
            },
            "sandbox3": {"organisations": [{"value": "Jeff's Ferret Zoo"}]},
        } == out
