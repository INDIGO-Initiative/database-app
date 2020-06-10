import jsonpointer
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from jsondataferret.models import Record


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
    # record is nullable for historical data - it should be NOT NULL really
    record = models.ForeignKey(Record, on_delete=models.PROTECT, null=True, blank=True)

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
    pass


class Project(BaseModel):
    pass


class ProjectImport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    data = JSONField(default=dict)
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
