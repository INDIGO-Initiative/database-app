import os

from django.test import TestCase  # noqa

import indigo.utils

SPREADSHEET_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "spreadsheetform_guides"
)


class GetProjectSpreadsheetVersion(TestCase):
    def test_v1(self):
        assert 1 == indigo.utils.get_project_spreadsheet_version(
            os.path.join(SPREADSHEET_DIR, "project_v001.xlsx")
        )

    def test_v2(self):
        assert 2 == indigo.utils.get_project_spreadsheet_version(
            os.path.join(SPREADSHEET_DIR, "project_v002.xlsx")
        )
