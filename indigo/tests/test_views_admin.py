import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.test import TestCase  # noqa
from django.urls import reverse

from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.models import AdminUserHasPermissionsForProject, Project, ProjectImport


class AdminModerateTests(TestCase):
    def test_organisation_admin_can_moderate(self):
        """
        Admin users try to moderate something; it should work.
        """
        # Create data
        type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        project_record = jsondataferret.models.Record.objects.create(
            type=type_organisation, public_id="INDIGO-ORG-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_organisation,
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
                "indigo_admin_organisation_moderate",
                kwargs={"public_id": "INDIGO-ORG-0001"},
            ),
            {"action_" + str(edits[0].id): "approve", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - it should now be approved!
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        self.assertIsNotNone(edits[0].approval_event)

    def test_organisation_data_steward_can_not_moderate(self):
        """
        Data Steward users try to moderate something; it should be quietly ignored.
        """
        # Create data
        type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        project_record = jsondataferret.models.Record.objects.create(
            type=type_organisation, public_id="INDIGO-ORG-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_organisation,
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
                "indigo_admin_organisation_moderate",
                kwargs={"public_id": "INDIGO-ORG-0001"},
            ),
            {"action_" + str(edits[0].id): "approve", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 200)

        # Test data - it should not be approved
        edits = jsondataferret.models.Edit.objects.filter()
        self.assertEqual(len(edits), 1)
        self.assertIsNone(edits[0].approval_event)


class AdminChangeStatusTests(TestCase):
    def test_organisation_data_steward_can_not_make_public_immediately(self):
        """
        Data Steward users try to make something public immediately; this is the one combination that should fail.
        """
        # Create data
        type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        organisation_record = jsondataferret.models.Record.objects.create(
            type=type_organisation, public_id="INDIGO-ORG-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_organisation,
                    organisation_record,
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
                "indigo_admin_organisation_change_status",
                kwargs={"public_id": "INDIGO-ORG-0001"},
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

    def test_organisation_admin_can_make_public_with_moderation(self):
        self._test_organisation_can_make_public_with_moderation("admin")

    def test_organisation_data_steward_can_make_public_with_moderation(self):
        self._test_organisation_can_make_public_with_moderation("data_steward")

    def _test_organisation_can_make_public_with_moderation(self, permission_codename):
        """
        Users of specified permission try to make something public with moderation; it should work.
        """
        # Create data
        type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        organisation_record = jsondataferret.models.Record.objects.create(
            type=type_organisation, public_id="INDIGO-ORG-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_organisation,
                    organisation_record,
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
                "indigo_admin_organisation_change_status",
                kwargs={"public_id": "INDIGO-ORG-0001"},
            ),
            {"status": "PUBLIC", "when": "moderate", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - there should now be a second edit - test its approval status
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 2)
        self.assertIsNone(edits[1].approval_event)

    def test_organisation_admin_can_make_public_immediately(self):
        self._test_organisation_can_make_change_immediately("admin", "PUBLIC")

    def test_organisation_data_steward_can_make_private_immediately(self):
        self._test_organisation_can_make_change_immediately("data_steward", "PRIVATE")

    def _test_organisation_can_make_change_immediately(
        self, permission_codename, new_status
    ):

        """
        Users of specified permission try to set a new status immediately; it should work.
        """
        # Create data
        type_organisation = jsondataferret.models.Type.objects.create(
            public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
        )
        organisation_record = jsondataferret.models.Record.objects.create(
            type=type_organisation, public_id="INDIGO-ORG-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_organisation,
                    organisation_record,
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
                "indigo_admin_organisation_change_status",
                kwargs={"public_id": "INDIGO-ORG-0001"},
            ),
            {"status": new_status, "when": "immediate", "comment": "Test"},
        )
        self.assertEqual(response.status_code, 302)

        # Test data - there should now be a second edit - test its approval status
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 2)
        self.assertIsNotNone(edits[1].approval_event)


class AdminDataStewardsAccessingProjectTest(TestCase):
    def test_data_steward_user_with_permissions_can_access_project(self):
        self._test_data_steward_user_with_permissions_project_access(True)

    def test_data_steward_user_without_permissions_can_not_access_project(self):
        self._test_data_steward_user_with_permissions_project_access(False)

    def _test_data_steward_user_with_permissions_project_access(
        self, has_permission_and_access
    ):
        """
        By Default, Data Stewards can NOT access projects
        """
        # Create data
        type_project = jsondataferret.models.Type.objects.create(
            public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
        )
        project_record = jsondataferret.models.Record.objects.create(
            type=type_project, public_id="INDIGO-PROJ-0001"
        )
        jsondataferret.pythonapi.newevent.newEvent(
            [
                jsondataferret.pythonapi.newevent.NewEventData(
                    type_project,
                    project_record,
                    {},
                    approved=True,
                )
            ]
        )
        project = Project.objects.get(public_id="INDIGO-PROJ-0001")

        # Test data
        edits = jsondataferret.models.Edit.objects.filter().order_by("id")
        self.assertEqual(len(edits), 1)

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename="data_steward"
        )
        user.user_permissions.add(permission)
        p = AdminUserHasPermissionsForProject()
        p.user = user
        p.project = project
        p.permission_access = has_permission_and_access
        p.save()

        # Test by calling code directly
        self.assertEqual(
            len(Project.objects.filter_by_admin_user_can_access(user)),
            1 if has_permission_and_access else 0,
        )

        # Test by making requests
        self.client.login(username="testuser", password="1234")

        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_index",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_download_form",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_download_simple_form",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_import_form",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        pi = ProjectImport()
        pi.user = user
        pi.project = project
        pi.save()
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_import_form_stage_2",
                    kwargs={"public_id": "INDIGO-PROJ-0001", "import_id": pi.id},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_change_status",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_moderate",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_history",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_data_quality_report",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        # This page is for admins only, not data stewards
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_project_admin_users",
                    kwargs={"public_id": "INDIGO-PROJ-0001"},
                )
            ).status_code,
            302,
        )

        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_event_index",
                    kwargs={"event_id": edits[0].creation_event.public_id},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "indigo_admin_edit_index",
                    kwargs={"edit_id": edits[0].public_id},
                )
            ).status_code,
            200 if has_permission_and_access else 403,
        )
