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
                    {
                        "contact": {
                            "name": {"value": "Bob"},
                            "email": {"value": "bob@test.com"},
                        },
                        "address": {"value": None},
                        "country": {"value": None},
                        "org-ids": {
                            "other": {"value": None},
                            "charity": {"value": None},
                            "company": {"value": None},
                        },
                        "website": {"value": None},
                        "postcode": {"value": None},
                    },
                    approved=True,
                )
            ]
        )

    def test_no_orgs(self):

        input = {"name": {"value": "Project With Ferrets"}}

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 1 == len(out)
        assert {
            "name": {"value": "Project With Ferrets"},
            "organisations": None,
        } == out[0].data

    def test_one_existing_org_with_changes(self):
        input = {
            "name": {"value": "Project With Ferrets"},
            "organisations": [
                {
                    "id": "ORG1",
                    "contact": {
                        "name": {"value": "Bob Prescot"},
                        "email": {"value": "bob.prescot@test.com"},
                    },
                    "address": {"value": None},
                    "country": {"value": None},
                    "org-ids": {
                        "other": {"value": None},
                        "charity": {"value": None},
                        "company": {"value": None},
                    },
                    "website": {"value": None},
                    "postcode": {"value": None},
                }
            ],
        }

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 2 == len(out)
        assert {
            "name": {"value": "Project With Ferrets"},
            "organisations": None,
        } == out[0].data
        # The org is different than current value so an edit exists for the org
        assert {
            "org-ids": {
                "company": {"value": None},
                "charity": {"value": None},
                "other": {"value": None},
            },
            "contact": {
                "name": {"value": "Bob Prescot"},
                "email": {"value": "bob.prescot@test.com"},
            },
            "website": {"value": None},
            "address": {"value": None},
            "postcode": {"value": None},
            "country": {"value": None},
        } == out[1].data

    def test_one_existing_org_with_no_changes(self):
        input = {
            "name": {"value": "Project With Ferrets"},
            "organisations": [
                {
                    "id": "ORG1",
                    "contact": {
                        "name": {"value": "Bob"},
                        "email": {"value": "bob@test.com"},
                    },
                    "address": {"value": None},
                    "country": {"value": None},
                    "org-ids": {
                        "other": {"value": None},
                        "charity": {"value": None},
                        "company": {"value": None},
                    },
                    "website": {"value": None},
                    "postcode": {"value": None},
                }
            ],
        }

        out = indigo.processdata.extract_edits_from_project_import(
            self.project_record, input
        )

        assert 1 == len(out)
        assert {
            "name": {"value": "Project With Ferrets"},
            "organisations": None,
        } == out[0].data
        # The org is same as current value so no edit exists for the org
