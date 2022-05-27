import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.test import TestCase  # noqa
from django.urls import reverse

from indigo import TYPE_PIPELINE_PUBLIC_ID


class AdminModerateTests(TestCase):
    def test_pipeline_admin_can_moderate(self):
        """
        Admin users try to moderate something; it should work.
        """
        # Create data
        type_pipeline = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PIPELINE_PUBLIC_ID, title="Pipeline"
        )
        project_record = jsondataferret.models.Record.objects.create(
            type=type_pipeline, public_id="INDIGO-PL-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_pipeline, project_record, {}, approved=False,
                )
            ]
        )

        # Test data - it should not be approved
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        self.assertIsNone(edits[0].approval_event)

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename="admin"
        )
        user.user_permissions.add(permission)

        # Make request
        self.client.login(username="testuser", password="1234")
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        response = self.client.post(
            reverse(
                "indigo_admin_pipeline_moderate", kwargs={"public_id": "INDIGO-PL-0001"}
            ),
            {"action_" + str(edits[0].id): "approve", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - it should now be approved!
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        self.assertIsNotNone(edits[0].approval_event)

    def test_pipeline_data_steward_can_note_moderate(self):
        """
        Data Steward users try to moderate something; it should be quietly ignored.
        """
        # Create data
        type_pipeline = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PIPELINE_PUBLIC_ID, title="Pipeline"
        )
        project_record = jsondataferret.models.Record.objects.create(
            type=type_pipeline, public_id="INDIGO-PL-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_pipeline, project_record, {}, approved=False,
                )
            ]
        )

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename="data_steward"
        )
        user.user_permissions.add(permission)

        # Make request
        self.client.login(username="testuser", password="1234")
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        response = self.client.post(
            reverse(
                "indigo_admin_pipeline_moderate", kwargs={"public_id": "INDIGO-PL-0001"}
            ),
            {"action_" + str(edits[0].id): "approve", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 200)

        # Test data - it should not be approved
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        self.assertIsNone(edits[0].approval_event)
