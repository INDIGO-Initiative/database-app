import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.test import TestCase  # noqa

from indigo import TYPE_PROJECT_PUBLIC_ID
from indigo.dataqualityreport import DataQualityReportForAllProjects


class GetSingleFieldStatisticsAcrossAllProjectsForFieldTest(TestCase):
    def create_records(self, inputs):
        type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        for project_id, project_data in inputs.items():
            project_record = jsondataferret.models.Record.objects.create(
                type=type_project, public_id=project_id
            )
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type_project, project_record, project_data, approved=True,
                    )
                ]
            )

    def test_public_project_with_public_data(self):
        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "stage_development": {
                    "value": "Early-stage design",
                    "status": "PUBLIC",
                },
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_single_field_statistics_for_field(
            {
                "key": "/stage_development/value",
                "title": "Stage of Development - (Value)",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_public_value"] == 1
        assert data["count_public_projects_without_public_value"] == 0

    def test_private_project_with_public_data(self):
        inputs = {
            "PROJ1": {
                "status": "PRIVATE",
                "stage_development": {
                    "value": "Early-stage design",
                    "status": "PUBLIC",
                },
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_single_field_statistics_for_field(
            {
                "key": "/stage_development/value",
                "title": "Stage of Development - (Value)",
            }
        )

        assert data["count_public_projects"] == 0
        assert data["count_public_projects_with_public_value"] == 0
        assert data["count_public_projects_without_public_value"] == 0

    def test_public_project_with_public_data_numbers(self):
        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "overall_project_finance": {
                    "total_investment_commitment": {
                        "amount": {"min": {"value": 100, "status": "PUBLIC"}}
                    }
                },
            },
            "PROJ2": {
                "status": "PUBLIC",
                "overall_project_finance": {
                    "total_investment_commitment": {
                        "amount": {"min": {"value": 0, "status": "PUBLIC"}}
                    }
                },
            },
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_single_field_statistics_for_field(
            {
                "key": "/overall_project_finance/total_investment_commitment/amount/min/value",
                "title": "Overall project finance - Total investment commitment - Amount - Min - (Value)",
            }
        )

        assert data["count_public_projects"] == 2
        assert data["count_public_projects_with_public_value"] == 2
        assert data["count_public_projects_without_public_value"] == 0

    def test_public_project_with_no_data(self):
        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "stage_development": {"value": "", "status": "PUBLIC"},
            },
            "PROJ2": {
                "status": "PUBLIC",
                "stage_development": {"value": None, "status": "PUBLIC"},
            },
            "PROJ3": {
                "status": "PUBLIC",
                "stage_development": {"value": "             ", "status": "PUBLIC"},
            },
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_single_field_statistics_for_field(
            {
                "key": "/stage_development/value",
                "title": "Stage of Development - (Value)",
            }
        )

        assert data["count_public_projects"] == 3
        assert data["count_public_projects_with_public_value"] == 0
        assert data["count_public_projects_without_public_value"] == 3

    def test_public_project_with_private_data(self):
        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "stage_development": {
                    "value": "Early-stage design",
                    "status": "PRIVATE",
                },
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_single_field_statistics_for_field(
            {
                "key": "/stage_development/value",
                "title": "Stage of Development - (Value)",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_public_value"] == 0
        assert data["count_public_projects_without_public_value"] == 1


class GetListFieldStatisticsAcrossAllProjectsForFieldTest(TestCase):
    def create_records(self, inputs):
        type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        for project_id, project_data in inputs.items():
            project_record = jsondataferret.models.Record.objects.create(
                type=type_project, public_id=project_id
            )
            jsondataferret.pythonapi.newevent.newEvent(
                [
                    jsondataferret.pythonapi.newevent.NewEventData(
                        type_project, project_record, project_data, approved=True,
                    )
                ]
            )

    def test_public_project_with_public_data(self):
        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "delivery_locations": [
                    {"location_name": {"value": "A City"}, "status": "PUBLIC",}
                ],
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_at_least_one_public_value"] == 1
        assert data["count_public_projects_without_any_public_values"] == 0

    def test_private_project_with_public_data(self):
        inputs = {
            "PROJ1": {
                "status": "PRIVATE",
                "delivery_locations": [
                    {"location_name": {"value": "A City"}, "status": "PUBLIC",}
                ],
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 0
        assert data["count_public_projects_with_at_least_one_public_value"] == 0
        assert data["count_public_projects_without_any_public_values"] == 0

    def test_public_project_with_empty_list_data(self):
        inputs = {"PROJ1": {"status": "PUBLIC", "delivery_locations": []}}

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_at_least_one_public_value"] == 0
        assert data["count_public_projects_without_any_public_values"] == 1

    def test_public_project_with_no_key_for_data(self):
        inputs = {"PROJ1": {"status": "PUBLIC",}}

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_at_least_one_public_value"] == 0
        assert data["count_public_projects_without_any_public_values"] == 1

    def test_public_project_with_private_data(self):

        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "delivery_locations": [
                    {"location_name": {"value": "A City"}, "status": "PRIVATE",}
                ],
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_at_least_one_public_value"] == 0
        assert data["count_public_projects_without_any_public_values"] == 1

    def test_public_project_with_private_and_public_data(self):

        inputs = {
            "PROJ1": {
                "status": "PUBLIC",
                "delivery_locations": [
                    {"location_name": {"value": "A Secret City"}, "status": "PRIVATE",},
                    {"location_name": {"value": "A City"}, "status": "PUBLIC",},
                ],
            }
        }

        self.create_records(inputs)

        data_quality_report = DataQualityReportForAllProjects()
        data = data_quality_report.get_list_field_statistics_for_field(
            {
                "key": "/delivery_locations",
                "title": "Delivery Locations",
                "type": "list",
            }
        )

        assert data["count_public_projects"] == 1
        assert data["count_public_projects_with_at_least_one_public_value"] == 1
        assert data["count_public_projects_without_any_public_values"] == 0
