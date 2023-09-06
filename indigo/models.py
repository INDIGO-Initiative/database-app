import jsonpointer
from django.conf import settings
from django.db import models
from jsondataferret.models import Record

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_PUBLIC_ID,
)


class Indigo(models.Model):
    class Meta:
        managed = False
        permissions = (
            ("admin", "Admin - All admin tasks on Indigo data"),
            (
                "data_steward",
                "Data Steward - View all Indigo data, submit edits for moderation, can make private/disputed",
            ),
        )


class BaseModel(models.Model):
    public_id = models.CharField(max_length=200, unique=True)
    exists = models.BooleanField(default=False)
    status_public = models.BooleanField(default=False)
    data_public = models.JSONField(default=dict)
    data_private = models.JSONField(default=dict)
    data_sandboxes = models.JSONField(default=dict)
    # record is nullable for historical data - it should be NOT NULL really
    record = models.ForeignKey(Record, on_delete=models.PROTECT, null=True, blank=True)
    full_text_search_private = models.TextField(default="")

    def has_data_public_field(self, field):
        try:
            return bool(
                jsonpointer.resolve_pointer(
                    self.data_public,
                    field,
                )
            )
        except jsonpointer.JsonPointerException:
            return False

    def get_data_public_field(self, field):
        try:
            return jsonpointer.resolve_pointer(
                self.data_public,
                field,
            )
        except jsonpointer.JsonPointerException:
            return ""

    def has_data_private_field(self, field):
        try:
            return bool(
                jsonpointer.resolve_pointer(
                    self.data_private,
                    field,
                )
            )
        except jsonpointer.JsonPointerException:
            return False

    def get_data_private_field(self, field):
        try:
            return jsonpointer.resolve_pointer(
                self.data_private,
                field,
            )
        except jsonpointer.JsonPointerException:
            return ""

    class Meta:
        abstract = True


class Organisation(BaseModel):
    type_id = TYPE_ORGANISATION_PUBLIC_ID


class ProjectManager(models.Manager):
    def filter_by_admin_user_can_access(self, user):
        if user and user.has_perm("indigo.admin"):
            return self.all().order_by("public_id")
        elif user and user.has_perm("indigo.data_steward"):
            return self.raw(
                "SELECT indigo_project.* FROM indigo_project "
                + "JOIN indigo_adminuserhaspermissionsforproject ON indigo_adminuserhaspermissionsforproject.project_id = indigo_project.id "
                + "AND indigo_adminuserhaspermissionsforproject.user_id=%s AND indigo_adminuserhaspermissionsforproject.permission_access = %s "
                + "ORDER BY indigo_project.public_id ASC",
                [user.id, True],
            )
        else:
            return []


class Project(BaseModel):
    social_investment_prototype = models.BooleanField(
        default=False, null=False, blank=True
    )
    data_quality_report_counts_by_priority = models.JSONField(default=dict)
    objects = ProjectManager()


class Fund(BaseModel):
    type_id = TYPE_FUND_PUBLIC_ID


class AssessmentResource(BaseModel):
    type_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class Pipeline(BaseModel):
    type_id = TYPE_PIPELINE_PUBLIC_ID


class JoiningUpInitiative(BaseModel):
    type_id = TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID


class BaseModelImport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file_data = models.BinaryField(null=True, blank=True)
    file_not_valid = models.BooleanField(null=True, blank=True)
    exception = models.BooleanField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    imported = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class ProjectImport(BaseModelImport):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="imports",
    )


class PipelineImport(BaseModelImport):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="imports",
    )


class ProjectIncludesOrganisation(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="includes_organisations",
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="included_by_projects",
    )
    in_current_data = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            "project",
            "organisation",
        )


class ProjectIncludesFund(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="includes_funds",
    )
    fund = models.ForeignKey(
        Fund,
        on_delete=models.PROTECT,
        related_name="included_by_projects",
    )
    in_current_data = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            "project",
            "fund",
        )


class PipelineIncludesOrganisation(models.Model):
    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.PROTECT,
        related_name="includes_organisations",
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.PROTECT,
        related_name="included_by_pipelines",
    )
    in_current_data = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            "pipeline",
            "organisation",
        )


class Sandbox(models.Model):
    public_id = models.CharField(max_length=200, unique=True)
    title = models.TextField(default="")


class AdminUserHasPermissionsForProject(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=False, blank=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=False, blank=False
    )
    # At the moment, there is only one permission possible to give
    # Access includes read, write, change status
    permission_access = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "user")
