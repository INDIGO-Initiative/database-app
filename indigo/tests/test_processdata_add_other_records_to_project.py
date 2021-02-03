import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.test import TestCase  # noqa

import indigo.processdata
from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID


class ProcessAddOtherRecordsToProject(TestCase):
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
                    {
                        "status": "PUBLIC",
                        "name": {"value": "Bob's Org"},
                        "contact": {
                            "name": {"value": "Bob"},
                            "email": {"value": "bob@test.com"},
                        },
                    },
                    approved=True,
                )
            ]
        )

    def test_no_orgs(self):

        input = {"name": {"value": "Project With Ferrets"}}

        out = indigo.processdata.add_other_records_to_project("PROJ1", input)

        assert {
            "name": {"value": "Project With Ferrets"},
            "id": "PROJ1",
            "organisations": [],
        } == out

    def test_org_not_exist(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "service_provisions": [{"organisation_id": {"value": "ORG1576597597"}}],
        }
        out = indigo.processdata.add_other_records_to_project("PROJ1", input)

        assert {
            "name": {"value": "Project With Ferrets"},
            "service_provisions": [{"organisation_id": {"value": "ORG1576597597"}}],
            "id": "PROJ1",
            "organisations": [],
        } == out

    def test_org_in_field(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "service_provisions": [{"organisation_id": {"value": "ORG1"}}],
        }

        out = indigo.processdata.add_other_records_to_project("PROJ1", input)

        assert {
            "name": {"value": "Project With Ferrets"},
            "service_provisions": [
                {
                    "organisation_id": {"value": "ORG1"},
                    "organisation_names": {"organisation_id": {"value": "Bob's Org"}},
                }
            ],
            "id": "PROJ1",
            "organisations": [
                {
                    "id": "ORG1",
                    "name": {"value": "Bob's Org"},
                    "org-ids": {
                        "company": {"value": None},
                        "charity": {"value": None},
                        "other": {"value": None},
                    },
                    "contact": {
                        "name": {"value": "Bob"},
                        "email": {"value": "bob@test.com"},
                    },
                    "website": {"value": None},
                    "address": {"value": None},
                    "postcode": {"value": None},
                    "country": {"value": None},
                }
            ],
        } == out

    def test_org_in_comma_seperated_field(self):

        input = {
            "name": {"value": "Project With Ferrets"},
            "results": [{"outcomes_validator_organisation_ids": {"value": "ORG1,"}}],
        }

        out = indigo.processdata.add_other_records_to_project("PROJ1", input)

        assert {
            "name": {"value": "Project With Ferrets"},
            "results": [{"outcomes_validator_organisation_ids": {"value": "ORG1,"}}],
            "id": "PROJ1",
            "organisations": [
                {
                    "id": "ORG1",
                    "name": {"value": "Bob's Org"},
                    "org-ids": {
                        "company": {"value": None},
                        "charity": {"value": None},
                        "other": {"value": None},
                    },
                    "contact": {
                        "name": {"value": "Bob"},
                        "email": {"value": "bob@test.com"},
                    },
                    "website": {"value": None},
                    "address": {"value": None},
                    "postcode": {"value": None},
                    "country": {"value": None},
                }
            ],
        } == out
