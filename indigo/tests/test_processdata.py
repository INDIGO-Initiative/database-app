import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.test import TestCase  # noqa

import indigo.processdata
from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID


class ProcessExtractEditsFromProjectImport(TestCase):
    type_project = None
    type_organisation = None
    project_record = None
    organisation_1_record = None

    def setUp(self):
        self.type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        self.type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        self.project_record = jsondataferret.models.Record.objects.create(
            type=self.type_project, public_id="PROJ1"
        )
        self.organisation_1_record = jsondataferret.models.Record.objects.create(
            type=self.type_organisation, public_id="ORG1"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    self.type_organisation,
                    self.organisation_1_record,
                    {"name": "Organisation One", "type": "Type Ferrety"},
                    approved=True,
                )
            ]
        )

    def test_no_orgs(self):

        input = {"project_name": {"value": "Project With Ferrets"}}

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 1 == len(out)
        assert {"project_name": {"value": "Project With Ferrets"}} == out[0].data

    def test_one_existing_org_with_changes(self):
        input = {
            "project_name": {"value": "Project With Ferrets"},
            "outcome_funds": [
                {
                    "title": "Bobs Fund",
                    "definition": "BOB-FUND",
                    "organisation": {
                        "id": "ORG1",
                        "name": "Organisation 1",
                        "type": "A serious Organisation",
                    },
                }
            ],
        }

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 2 == len(out)
        assert {
            "project_name": {"value": "Project With Ferrets"},
            "outcome_funds": [
                {
                    "title": "Bobs Fund",
                    "definition": "BOB-FUND",
                    "organisation": {"id": "ORG1", "name": None, "type": None},
                }
            ],
        } == out[0].data
        # The org is different than current value so an edit exists for the org
        assert {"name": "Organisation 1", "type": "A serious Organisation"} == out[
            1
        ].data

    def test_one_existing_org_with_no_changes(self):
        input = {
            "project_name": {"value": "Project With Ferrets"},
            "outcome_funds": [
                {
                    "title": "Bobs Fund",
                    "definition": "BOB-FUND",
                    "organisation": {
                        "id": "ORG1",
                        "name": "Organisation One",
                        "type": "Type Ferrety",
                    },
                }
            ],
        }

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 1 == len(out)
        assert {
            "project_name": {"value": "Project With Ferrets"},
            "outcome_funds": [
                {
                    "title": "Bobs Fund",
                    "definition": "BOB-FUND",
                    "organisation": {"id": "ORG1", "name": None, "type": None},
                }
            ],
        } == out[0].data
        # The org is same as current value so no edit exists for the org
