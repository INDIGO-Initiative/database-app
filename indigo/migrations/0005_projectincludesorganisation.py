# Generated by Django 3.0.7 on 2020-06-10 15:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indigo", "0004_projectimport"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectIncludesOrganisation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("in_current_data", models.BooleanField(default=False)),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="included_by_projects",
                        to="indigo.Organisation",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="includes_organisations",
                        to="indigo.Project",
                    ),
                ),
            ],
            options={
                "unique_together": {("project", "organisation")},
            },
        ),
    ]
