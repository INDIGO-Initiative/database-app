import jsonpointer
from django.contrib.postgres.fields import JSONField
from django.db import models


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
