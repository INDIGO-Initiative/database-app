"""Every address of the application admin must be locked down.

Rather than list the addresses by hand (and miss one added later), this walks all of them: it finds every route in
indigo/urls.py that starts "admin/", fills in dummy values for its parts, and tries each one both for reading (GET) and
for submitting (POST) as someone who should not get in."""
import re

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase  # noqa

import indigo.urls
from indigo.models import AdminUserHasPermissionsForProject, Project


def admin_routes():
    """(name, path with dummy values) for every route of the application admin."""
    routes = []
    for pattern in indigo.urls.urlpatterns:
        route = str(pattern.pattern)
        if not route.startswith("admin/"):
            continue
        path = re.sub(r"<(?:\w+:)?(\w+)>", "X", route)
        routes.append((pattern.name, "/app/" + path))
    return routes


# Refused means sent to log in (302), forbidden (403), or, for a submit to a page that only displays things, "method not
# allowed" (405): in each case nothing is shown or changed.
REFUSED = (302, 403, 405)


class EveryAdminAddressIsLockedDownTests(TestCase):
    def setUp(self):
        self.routes = admin_routes()

    def _login(self, codename=None):
        user = User.objects.create_user(username=codename or "plain", password="1234")
        if codename:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label="indigo", codename=codename
                )
            )
        client = Client()
        client.login(username=user.username, password="1234")
        return user, client

    def test_we_are_really_looking_at_the_admin(self):
        # Guards the test itself: if the routes could not be found, every check below would pass for nothing
        self.assertGreater(len(self.routes), 60)
        names = [name for name, path in self.routes]
        for expected in [
            "indigo_admin_project_edit",
            "indigo_admin_organisation_edit",
            "indigo_admin_project_new",
            "indigo_admin_fund_moderate",
            "indigo_admin_project_import_form",
            "indigo_admin_pipeline_change_status",
        ]:
            self.assertIn(expected, names)

    def test_anonymous_visitors_are_sent_to_log_in_on_every_address(self):
        client = Client()
        for name, path in self.routes:
            for method in (client.get, client.post):
                response = method(path)
                self.assertEqual(
                    response.status_code,
                    302,
                    f"{method.__name__.upper()} {path} ({name}) let an anonymous visitor in: {response.status_code}",
                )
                self.assertIn(
                    "/accounts/login/",
                    response.url,
                    f"{method.__name__.upper()} {path} ({name})",
                )

    def test_logged_in_users_without_permission_are_refused_on_every_address(self):
        user, client = self._login()
        for name, path in self.routes:
            for method in (client.get, client.post):
                response = method(path)
                self.assertIn(
                    response.status_code,
                    REFUSED,
                    f"{method.__name__.upper()} {path} ({name}) let in a user with no permissions: {response.status_code}",
                )

    def test_data_stewards_are_refused_on_every_address_that_is_for_admins(self):
        """Stewards may use the project, organisation and fund pages; everything else is for admins."""
        steward_may_use = (
            "project",
            "organisation",
            "fund",
            "sandbox",
            "organisation_search_json",
        )
        user, client = self._login("data_steward")
        for name, path in self.routes:
            if any(part in name for part in steward_may_use) or name in (
                "indigo_admin_index",
                "indigo_admin_organisation_goto",
                "indigo_admin_event_index",
                "indigo_admin_edit_index",
            ):
                continue
            for method in (client.get, client.post):
                response = method(path)
                self.assertIn(
                    response.status_code,
                    REFUSED,
                    f"{method.__name__.upper()} {path} ({name}) let in a data steward: {response.status_code}",
                )

    def test_stewards_cannot_reach_a_project_they_have_not_been_given(self):
        """Every address about one project checks that a steward has been given that project."""
        import jsondataferret.models

        type = jsondataferret.models.Type.objects.create(
            public_id="project", title="Project"
        )
        record = jsondataferret.models.Record.objects.create(type=type, public_id="X")
        Project.objects.create(public_id="X", exists=True, record=record)
        user, client = self._login("data_steward")
        project_routes = [
            (name, path)
            for name, path in self.routes
            if name.startswith("indigo_admin_project_")
            and "<" not in path
            and "/project/X" in path
        ]
        self.assertGreater(len(project_routes), 8)
        for name, path in project_routes:
            for method in (client.get, client.post):
                response = method(path)
                self.assertIn(
                    response.status_code,
                    REFUSED,
                    f"{method.__name__.upper()} {path} ({name}) let a steward into a project they have not been given: {response.status_code}",
                )
        # and once given the project, they can see it
        AdminUserHasPermissionsForProject.objects.create(
            user=user,
            project=Project.objects.get(public_id="X"),
            permission_access=True,
        )
        self.assertEqual(client.get("/app/admin/project/X").status_code, 200)


class EventAndEditPagesAreLockedDownTests(TestCase):
    """The pages for one event or one edit decide who may look by the records they are about, so they need real ones."""

    def setUp(self):
        import jsondataferret.models
        import jsondataferret.pythonapi.newevent as newevent

        self.admin = User.objects.create_user(username="admin", password="1234")
        self.admin.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.steward = User.objects.create_user(username="steward", password="1234")
        self.steward.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="indigo", codename="data_steward"
            )
        )
        self.pages = {}
        for type_id in ["project", "fund", "pipeline"]:
            type = jsondataferret.models.Type.objects.create(
                public_id=type_id, title=type_id
            )
            record = jsondataferret.models.Record.objects.create(
                type=type, public_id=f"{type_id.upper()}1"
            )
            newevent.newEvent(
                [newevent.NewEventData(type, record, {"name": {"value": "A"}})],
                user=self.admin,
            )
            edit = jsondataferret.models.Edit.objects.get(record=record)
            self.pages[type_id] = (
                f"/app/admin/event/{edit.creation_event.public_id}",
                f"/app/admin/edit/{edit.public_id}",
            )

    def _get(self, user, url):
        client = Client()
        if user:
            client.login(username=user.username, password="1234")
        return client.get(url).status_code

    def test_visitors_cannot_see_any_of_them(self):
        for type_id, urls in self.pages.items():
            for url in urls:
                self.assertEqual(self._get(None, url), 302, url)

    def test_admins_can_see_them(self):
        for type_id, urls in self.pages.items():
            for url in urls:
                self.assertEqual(self._get(self.admin, url), 200, url)

    def test_stewards_only_see_what_is_about_things_they_may_use(self):
        # a project they have not been given, and a type that is for admins only: refused
        for type_id in ["project", "pipeline"]:
            for url in self.pages[type_id]:
                self.assertIn(self._get(self.steward, url), (302, 403), url)
        # funds are open to stewards
        for url in self.pages["fund"]:
            self.assertEqual(self._get(self.steward, url), 200, url)
        # and a project they have been given
        AdminUserHasPermissionsForProject.objects.create(
            user=self.steward,
            project=Project.objects.get(public_id="PROJECT1"),
            permission_access=True,
        )
        for url in self.pages["project"]:
            self.assertEqual(self._get(self.steward, url), 200, url)


class EditDetailPageTests(TestCase):
    """The page for one edit used to crash for an edit that has not been moderated yet."""

    def setUp(self):
        import jsondataferret.models
        import jsondataferret.pythonapi.newevent as newevent

        user = User.objects.create_user(username="admin", password="1234")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="indigo", codename="admin")
        )
        self.client.login(username="admin", password="1234")
        type = jsondataferret.models.Type.objects.create(public_id="fund", title="Fund")
        self.record = jsondataferret.models.Record.objects.create(
            type=type, public_id="FUND1"
        )
        newevent.newEvent(
            [newevent.NewEventData(type, self.record, {"name": {"value": "A"}})],
            user=user,
        )
        self.newevent = newevent
        self.type = type

    def _edit(self):
        import jsondataferret.models

        return jsondataferret.models.Edit.objects.get(record=self.record)

    def test_an_edit_waiting_for_moderation_can_be_viewed(self):
        edit = self._edit()
        response = self.client.get(f"/app/admin/edit/{edit.public_id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not Moderated yet")
        # The Creation row's button opens the event that created the edit
        self.assertContains(
            response,
            f'href="/app/admin/event/{edit.creation_event.public_id}" class="btn btn-primary btn-sm">View change</a>',
        )

    def test_an_approved_edit_links_to_both_events_correctly(self):
        edit = self._edit()
        self.newevent.newEvent([self.newevent.NewEventApproval(edit)])
        edit.refresh_from_db()
        response = self.client.get(f"/app/admin/edit/{edit.public_id}")
        self.assertEqual(response.status_code, 200)
        created = f'href="/app/admin/event/{edit.creation_event.public_id}"'
        approved = f'href="/app/admin/event/{edit.approval_event.public_id}"'
        self.assertContains(response, created)
        self.assertContains(response, approved)

    def test_a_refused_edit_can_be_viewed(self):
        edit = self._edit()
        self.newevent.newEvent([self.newevent.NewEventRejection(edit)])
        edit.refresh_from_db()
        response = self.client.get(f"/app/admin/edit/{edit.public_id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Refused")
