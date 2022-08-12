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
                    type_pipeline,
                    project_record,
                    {},
                    approved=False,
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
                    type_pipeline,
                    project_record,
                    {},
                    approved=False,
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


class AdminChangeStatusTests(TestCase):
    def test_pipeline_data_steward_can_not_make_public_immediately(self):
        """
        Data Steward users try to make something public immediately; this is the one combination that should fail.
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
                    type_pipeline,
                    project_record,
                    {},
                    approved=True,
                )
            ]
        )

        # Test data
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 1)

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
                "indigo_admin_pipeline_change_status",
                kwargs={"public_id": "INDIGO-PL-0001"},
            ),
            {"status": "PUBLIC", "when": "immediate", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            "form",
            None,
            "With this access level, you can not make something public without submitting if for moderation.",
        )

        # Test data - there should not be any new ones.
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 1)

    def test_pipeline_admin_can_make_public_with_moderation(self):
        self._test_pipeline_can_make_public_with_moderation("admin")

    def test_pipeline_data_steward_can_make_public_with_moderation(self):
        self._test_pipeline_can_make_public_with_moderation("data_steward")

    def _test_pipeline_can_make_public_with_moderation(self, permission_codename):
        """
        Users of specified permission try to make something public with moderation; it should work.
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
                    type_pipeline,
                    project_record,
                    {},
                    approved=True,
                )
            ]
        )

        # Test data
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 1)

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename=permission_codename
        )
        user.user_permissions.add(permission)

        # Make request
        self.client.login(username="testuser", password="1234")
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        response = self.client.post(
            reverse(
                "indigo_admin_pipeline_change_status",
                kwargs={"public_id": "INDIGO-PL-0001"},
            ),
            {"status": "PUBLIC", "when": "moderate", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - there should now be a second edit - test its approval status
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 2)
        self.assertIsNone(edits[1].approval_event)

    def test_pipeline_admin_can_make_public_immediately(self):
        self._test_pipeline_can_make_change_immediately("admin", "PUBLIC")

    def test_pipeline_data_steward_can_make_private_immediately(self):
        self._test_pipeline_can_make_change_immediately("data_steward", "PRIVATE")

    def _test_pipeline_can_make_change_immediately(
        self, permission_codename, new_status
    ):

        """
        Users of specified permission try to set a new status immediately; it should work.
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
                    type_pipeline,
                    project_record,
                    {},
                    approved=True,
                )
            ]
        )

        # Test data
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 1)

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename=permission_codename
        )
        user.user_permissions.add(permission)

        # Make request
        self.client.login(username="testuser", password="1234")
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        response = self.client.post(
            reverse(
                "indigo_admin_pipeline_change_status",
                kwargs={"public_id": "INDIGO-PL-0001"},
            ),
            {"status": new_status, "when": "immediate", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - there should now be a second edit - test its approval status
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 2)
        self.assertIsNotNone(edits[1].approval_event)
