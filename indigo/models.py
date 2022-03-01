import jsonpointer
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from jsondataferret.models import Record

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
)


class Indigo(models.Model):
    class Meta:
        managed = False
        permissions = (("admin", "Admin - All admin tasks on Indigo data"),)


class BaseModel(models.Model):
    public_id = models.CharField(max_length=200, unique=True)
    exists = models.BooleanField(default=False)
    status_public = models.BooleanField(default=False)
    data_public = JSONField(default=dict)
    data_private = JSONField(default=dict)
    data_sandboxes = JSONField(default=dict)
    # record is nullable for historical data - it should be NOT NULL really
    record = models.ForeignKey(Record, on_delete=models.PROTECT, null=True, blank=True)
    full_text_search_private = models.TextField(default="")

    def has_data_public_field(self, field):
        try:
            return bool(jsonpointer.resolve_pointer(self.data_public, field,))
        except jsonpointer.JsonPointerException:
            return False

    def get_data_public_field(self, field):
        try:
            return jsonpointer.resolve_pointer(self.data_public, field,)
        except jsonpointer.JsonPointerException:
            return ""

    def has_data_private_field(self, field):
        try:
            return bool(jsonpointer.resolve_pointer(self.data_private, field,))
        except jsonpointer.JsonPointerException:
            return False

    def get_data_private_field(self, field):
        try:
            return jsonpointer.resolve_pointer(self.data_private, field,)
        except jsonpointer.JsonPointerException:
            return ""

    class Meta:
        abstract = True


class Organisation(BaseModel):
    type_id = TYPE_ORGANISATION_PUBLIC_ID


class Project(BaseModel):
    social_investment_prototype = models.BooleanField(
        default=False, null=False, blank=True
    )
    data_quality_report_counts_by_priority = JSONField(default=dict)


class Fund(BaseModel):
    type_id = TYPE_FUND_PUBLIC_ID


class AssessmentResource(BaseModel):
    type_id = TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class ProjectImport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file_data = models.BinaryField(null=True, blank=True)
    file_not_valid = models.BooleanField(null=True, blank=True)
    exception = models.BooleanField(null=True, blank=True)
    data = JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    imported = models.DateTimeField(null=True, blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="imports",
    )


class ProjectIncludesOrganisation(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="includes_organisations",
    )
    organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, related_name="included_by_projects",
    )
    in_current_data = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            "project",
            "organisation",
        )


class ProjectIncludesFund(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, related_name="includes_funds",
    )
    fund = models.ForeignKey(
        Fund, on_delete=models.PROTECT, related_name="included_by_projects",
    )
    in_current_data = models.BooleanField(default=False)

    class Meta:
        unique_together = (
            "project",
            "fund",
        )


class Sandbox(models.Model):
    public_id = models.CharField(max_length=200, unique=True)
    title = models.TextField(default="")
