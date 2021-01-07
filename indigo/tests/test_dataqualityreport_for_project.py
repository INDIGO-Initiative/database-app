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
