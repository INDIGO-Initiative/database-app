"""The project and organisation admin pages are class based like the other types; check the parts that are special to them."""
import jsondataferret.models
import jsondataferret.pythonapi.newevent
from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.models import AdminUserHasPermissionsForProject, Project


def _user(username, codename):
    user = User.objects.create_user(username, password="pw")
    user.user_permissions.add(
        Permission.objects.get(codename=codename, content_type__app_label="indigo")
    )
    return user


def _record(type_public_id, public_id, name):
    type = jsondataferret.models.Type.objects.get_or_create(
        public_id=type_public_id, defaults={"title": type_public_id}
    )[0]
    record = jsondataferret.models.Record.objects.create(type=type, public_id=public_id)
    jsondataferret.pythonapi.newevent.newEvent(
        [
            jsondataferret.pythonapi.newevent.NewEventData(
                type, record, {"name": {"value": name}}, approved=True
            )
        ],
        comment="c",
    )
    return record


class AdminProjectClassBasedTests(TestCase):
    def test_a_steward_who_adds_a_project_can_see_it_but_not_other_projects(self):
        _record(TYPE_PROJECT_PUBLIC_ID, "INDIGO-POJ-0900", "Someone else's")
        steward = _user("steward", "data_steward")
        self.client.force_login(steward)
        response = self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        self.assertEqual(response.status_code, 302)
        mine = Project.objects.exclude(public_id="INDIGO-POJ-0900").get()
        self.assertTrue(
            AdminUserHasPermissionsForProject.objects.get(
                user=steward, project=mine
            ).permission_access
        )
        for page in ["index", "history", "moderate"]:
            url = reverse(
                f"indigo_admin_project_{page}", kwargs={"public_id": mine.public_id}
            )
            self.assertEqual(self.client.get(url).status_code, 200, page)
            url = reverse(
                f"indigo_admin_project_{page}", kwargs={"public_id": "INDIGO-POJ-0900"}
            )
            self.assertEqual(self.client.get(url).status_code, 403, page)

    def test_an_admin_adding_a_project_does_not_give_anyone_access(self):
        self.client.force_login(_user("admin", "admin"))
        self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        self.assertEqual(AdminUserHasPermissionsForProject.objects.count(), 0)

    def test_a_steward_only_lists_their_own_projects(self):
        _record(TYPE_PROJECT_PUBLIC_ID, "INDIGO-POJ-0900", "Someone else's")
        steward = _user("steward", "data_steward")
        self.client.force_login(steward)
        self.client.post(
            reverse("indigo_admin_project_new"), {"name": "Mine", "comment": "new"}
        )
        response = self.client.get(reverse("indigo_admin_project_list"))
        self.assertEqual(
            [p.public_id for p in response.context["items"]],
            [Project.objects.exclude(public_id="INDIGO-POJ-0900").get().public_id],
        )


@override_settings(
    FILE_UPLOAD_HANDLERS=["django.core.files.uploadhandler.TemporaryFileUploadHandler"]
)
class AdminOrganisationClassBasedTests(TestCase):
    def setUp(self):
        _record(TYPE_ORGANISATION_PUBLIC_ID, "INDIGO-ORG-0900", "Acme")
        self.client.force_login(_user("admin", "admin"))

    def test_blank_form_and_filled_form_download_as_spreadsheets(self):
        for name, kwargs in [
            ("indigo_admin_organisation_download_blank_form", {}),
            (
                "indigo_admin_organisation_download_form",
                {"public_id": "INDIGO-ORG-0900"},
            ),
        ]:
            response = self.client.get(reverse(name, kwargs=kwargs))
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response["Content-Type"], "application/vnd.ms-excel")
            self.assertEqual(response.content[:2], b"PK", name)

    def test_a_downloaded_form_can_be_uploaded_again(self):
        form = self.client.get(
            reverse(
                "indigo_admin_organisation_download_form",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            )
        ).content
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse(
                "indigo_admin_organisation_import_form",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            ),
            {
                "file": SimpleUploadedFile("organisation.xlsx", form),
                "comment": "round trip",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse(
                "indigo_admin_organisation_index",
                kwargs={"public_id": "INDIGO-ORG-0900"},
            ),
        )

    def test_the_search_page_and_list_are_the_same_page(self):
        for name in [
            "indigo_admin_organisation_list",
            "indigo_admin_organisation_search",
        ]:
            response = self.client.get(reverse(name), {"search": "Acme"})
            self.assertEqual(
                [o.public_id for o in response.context["items"]],
                ["INDIGO-ORG-0900"],
                name,
            )
            self.assertContains(response, "Go to ID", msg_prefix=name)
