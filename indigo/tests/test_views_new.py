import jsondataferret.models
from django.contrib.auth.models import Permission, User
from django.test import TestCase  # noqa

from indigo import (
    ID_PREFIX_BY_TYPE,
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import AssessmentResource, Fund, Organisation, Pipeline, Project


class TestViewsNew(TestCase):
    def test_new(self):
        # Create data
        types_and_models = [
            (
                jsondataferret.models.Type.objects.create(
                    public_id=TYPE_PROJECT_PUBLIC_ID, title="Project"
                ),
                Project,
            ),
            (
                jsondataferret.models.Type.objects.create(
                    public_id=TYPE_ORGANISATION_PUBLIC_ID, title="Organisation"
                ),
                Organisation,
            ),
            (
                jsondataferret.models.Type.objects.create(
                    public_id=TYPE_FUND_PUBLIC_ID, title="Fund"
                ),
                Fund,
            ),
            (
                jsondataferret.models.Type.objects.create(
                    public_id=TYPE_PIPELINE_PUBLIC_ID, title="Pipeline"
                ),
                Pipeline,
            ),
            (
                jsondataferret.models.Type.objects.create(
                    public_id=TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
                    title="Assessment Resource",
                ),
                AssessmentResource,
            ),
        ]

        # Create user
        user = User.objects.create_user(username="testuser", password="1234")
        permission = Permission.objects.get(
            content_type__app_label="indigo", codename="admin"
        )
        user.user_permissions.add(permission)

        self.client.login(username="testuser", password="1234")
        for type_, model in types_and_models:
            with self.subTest(params=type_):
                resp = self.client.post(
                    f"/app/admin/new_{type_.public_id}",
                    {"name": "A name", "comment": "A comment",},
                )
                self.assertEquals(
                    resp.url,
                    f"/app/admin/{type_.public_id}/{ID_PREFIX_BY_TYPE[type_.public_id]}0001",
                )
                resp = self.client.post(
                    f"/app/admin/new_{type_.public_id}",
                    {"name": "Another name", "comment": "Another comment",},
                )
                self.assertEquals(
                    resp.url,
                    f"/app/admin/{type_.public_id}/{ID_PREFIX_BY_TYPE[type_.public_id]}0002",
                )
                objects = model.objects.order_by("public_id").all()
                self.assertEquals(len(objects), 2)
                self.assertEquals(
                    objects[0].public_id, f"{ID_PREFIX_BY_TYPE[type_.public_id]}0001"
                )
                self.assertEquals(objects[0].data_private["name"]["value"], "A name")
                self.assertEquals(
                    objects[1].public_id, f"{ID_PREFIX_BY_TYPE[type_.public_id]}0002"
                )
                self.assertEquals(
                    objects[1].data_private["name"]["value"], "Another name"
                )
