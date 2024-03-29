# Generated by Django 3.2.17 on 2023-09-06 10:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indigo", "0019_adminuserhaspermissionsforproject"),
    ]

    operations = [
        migrations.CreateModel(
            name="PipelineIncludesOrganisation",
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
                        related_name="included_by_pipelines",
                        to="indigo.organisation",
                    ),
                ),
                (
                    "pipeline",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="includes_organisations",
                        to="indigo.pipeline",
                    ),
                ),
            ],
            options={
                "unique_together": {("pipeline", "organisation")},
            },
        ),
    ]
