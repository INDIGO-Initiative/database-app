from copy import deepcopy

from django.test import TestCase  # noqa

from indigo.dataqualityreport import DataQualityReportForProject

PASSING_DATA = {}

# NEW_PROJECT_DATA is deliberately copied and pasted from the view instead of referencing a global constant or something
# This is because if a value is ever used to create a project, there is always the possibility some projects will exist
# with the old value and so we should test for that
NEW_PROJECT_DATA = {"name": {"value": "New Project"}}


class DataQualityReportForProjectTest(TestCase):
    def test_no_errors(self):
        dqr = DataQualityReportForProject(PASSING_DATA)
        errors = dqr.get_errors()

        assert 0 == len(errors)

    def test_new_project(self):
        dqr = DataQualityReportForProject(NEW_PROJECT_DATA)
        errors = dqr.get_errors()

        assert 0 == len(errors)

    def test_value_not_in_enum_list(self):
        data = deepcopy(PASSING_DATA)
        data["status"] = "Who knows"
        dqr = DataQualityReportForProject(data)
        errors = dqr.get_errors()

        assert 1 == len(errors)
        assert "value_not_in_enum_list" == errors[0].get_type()
        assert "Who knows" == errors[0].get_value()
        assert "PUBLIC" in errors[0].get_value_options()
        assert "status" == errors[0].get_path()

    def test_none_for_a_value(self):
        """An empty string can be turned to None by Spreadsheet Forms; test we correctly identify that as a missing value"""
        data = deepcopy(PASSING_DATA)
        data["alternative_names"] = {"value": None}
        dqr = DataQualityReportForProject(data)
        errors = dqr.get_errors()

        assert 1 == len(errors)
        assert "value_not_set" == errors[0].get_type()
        assert "alternative_names/value" == errors[0].get_path()

    def test_bad_date(self):
        data = deepcopy(PASSING_DATA)
        data["dates"] = {"outcomes_contract_signed": {"value": "23rd April 2020"}}
        dqr = DataQualityReportForProject(data)
        errors = dqr.get_errors()

        assert 1 == len(errors)
        assert "value_not_correct_pattern" == errors[0].get_type()
        assert "dates/outcomes_contract_signed/value" == errors[0].get_path()
        assert "23rd April 2020" == errors[0].get_value()
        assert (
            "Enter a date in format YYYY, YYYY-MM or YYYY-MM-DD"
            == errors[0].get_pattern_hint()
        )

    def test_not_a_number(self):
        data = deepcopy(PASSING_DATA)
        data["delivery_locations"] = [
            {"lat_lng": {"lat": {"value": "East a bit"}, "lng": {"value": 37.8}}},
            {"lat_lng": {"lat": {"value": None}, "lng": {"value": None}}},
        ]
        dqr = DataQualityReportForProject(data)
        errors = dqr.get_errors()

        assert 1 == len(errors)
        assert "value_not_a_number" == errors[0].get_type()
        assert "delivery_locations/0/lat_lng/lat/value" == errors[0].get_path()
        assert "East a bit" == errors[0].get_value()
