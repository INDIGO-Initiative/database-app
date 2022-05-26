import os

from django.core.exceptions import ValidationError
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


class GetOrganisationSpreadsheetVersion(TestCase):
    def test_v1(self):
        assert 1 == indigo.utils.get_organisation_spreadsheet_version(
            os.path.join(SPREADSHEET_DIR, "organisation_v001.xlsx")
        )

    def test_v2(self):
        assert 2 == indigo.utils.get_organisation_spreadsheet_version(
            os.path.join(SPREADSHEET_DIR, "organisation_v002.xlsx")
        )


class ValidateFundId(TestCase):
    def test_validate_fund_id_1(self):
        indigo.utils.validate_fund_id("INDIGO-FUND-0001")

    def test_validate_fund_id_2(self):
        with self.assertRaises(ValidationError):
            indigo.utils.validate_fund_id("INDIGO_FUND_0001")

    def test_validate_fund_id_3(self):
        with self.assertRaises(ValidationError):
            indigo.utils.validate_fund_id("INDIGO-FUND-001")


class ValidateOrganisationId(TestCase):
    def test_validate_organisation_id_1(self):
        indigo.utils.validate_organisation_id("INDIGO-ORG-0001")

    def test_validate_organisation_id_2(self):
        with self.assertRaises(ValidationError):
            indigo.utils.validate_organisation_id("INDIGO_ORG_0001")

    def test_validate_organisation_id_3(self):
        with self.assertRaises(ValidationError):
            indigo.utils.validate_organisation_id("INDIGO-ORG-001")
