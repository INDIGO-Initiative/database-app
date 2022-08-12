from django.test import TestCase  # noqa

import indigo.processdata


class ProcessFindUniqueOrganisationIdsReferencedInProjectData(TestCase):
    def test_none(self):

        input = {"name": {"value": "Project With Ferrets"}}

        out = (
            indigo.processdata.find_unique_organisation_ids_referenced_in_project_data(
                input
            )
        )

        assert 0 == len(out)

    def test_one(self):

        input = {
            "outcome_payment_commitments": [
                {
                    "organisation_id": {"value": "ORG-ODS"},
                    "organisation_role_category": {"value": "Corporate Giving"},
                    "maximum_potential_outcome_payment": {"value": 10000},
                }
            ]
        }

        out = (
            indigo.processdata.find_unique_organisation_ids_referenced_in_project_data(
                input
            )
        )

        assert 1 == len(out)
        assert "ORG-ODS" == out[0]

    def test_one_unique(self):

        input = {
            "outcome_payment_commitments": [
                {
                    "organisation_id": {"value": "ORG-ODS"},
                    "organisation_role_category": {"value": "Corporate Giving"},
                    "maximum_potential_outcome_payment": {"value": 10000},
                },
                {
                    "organisation_id": {"value": "ORG-ODS"},
                    "organisation_role_category": {"value": "Corporate Giving"},
                    "maximum_potential_outcome_payment": {"value": 999999910000},
                },
            ]
        }

        out = (
            indigo.processdata.find_unique_organisation_ids_referenced_in_project_data(
                input
            )
        )

        assert 1 == len(out)
        assert "ORG-ODS" == out[0]
