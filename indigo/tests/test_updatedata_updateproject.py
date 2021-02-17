import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.test import TestCase  # noqa

from indigo import TYPE_PROJECT_PUBLIC_ID
from indigo.models import Project, Sandbox


class UpdateDataUpdateProjectForSandboxData(TestCase):
    type_project = None
    type_organisation = None
    project_record = None

    def create_records(self, project_data):
        sandbox = Sandbox()
        sandbox.public_id = "s1"
        sandbox.title = "Sandbox"
        sandbox.save()
        self.type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        self.project_record = jsondataferret.models.Record.objects.create(
            type=self.type_project, public_id="PROJ1"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    self.type_project, self.project_record, project_data, approved=True,
                )
            ]
        )

    def test_no_sandbox_data(self):

        input = {
            "status": "PUBLIC",
            "stage_development": {"value": "Early-stage design", "status": "PUBLIC"},
        }

        self.create_records(input)

        project = Project.objects.get(public_id="PROJ1")

        assert project.data_sandboxes == {}

    def test_has_sandbox_data(self):

        input = {
            "status": "PUBLIC",
            "stage_development": {
                "value": "Early-stage design",
                "status": "SANDBOX",
                "sandboxes": "s1",
            },
        }

        self.create_records(input)

        project = Project.objects.get(public_id="PROJ1")

        assert project.data_sandboxes == {
            "s1": {
                "id": "PROJ1",
                "status": None,
                "organisations": [],
                "stage_development": {
                    "value": "Early-stage design",
                    "status": None,
                    "sandboxes": None,
                },
            }
        }
