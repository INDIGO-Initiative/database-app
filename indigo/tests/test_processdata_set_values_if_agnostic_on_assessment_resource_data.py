from django.test import TestCase  # noqa

from indigo.processdata import set_values_if_agnostic_on_assessment_resource_data


class ProcessDataSetValuesIfAgnosticOnAssessmentResourceData(TestCase):
    def test_nothing(self):
        data_in = {}

        data_out = set_values_if_agnostic_on_assessment_resource_data(data_in)

        assert data_out == {}

    def test_not_agnostic(self):
        data_in = {
            "scale": {"meso": "NO", "macro": "NO", "micro": "YES", "agnostic": "NO"}
        }

        data_out = set_values_if_agnostic_on_assessment_resource_data(data_in)

        assert data_out == {
            "scale": {"meso": "NO", "macro": "NO", "micro": "YES", "agnostic": "NO"}
        }

    def test_agnostic(self):
        data_in = {
            "scale": {"meso": "NO", "macro": "NO", "micro": "YES", "agnostic": "YES"}
        }

        data_out = set_values_if_agnostic_on_assessment_resource_data(data_in)

        assert data_out == {
            "scale": {"meso": "YES", "macro": "YES", "micro": "YES", "agnostic": "YES"}
        }

    def test_agnostic_with_intput_keys_missing(self):
        data_in = {"scale": {"agnostic": "YES"}}

        data_out = set_values_if_agnostic_on_assessment_resource_data(data_in)

        assert data_out == {
            "scale": {"meso": "YES", "macro": "YES", "micro": "YES", "agnostic": "YES"}
        }
