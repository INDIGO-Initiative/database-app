# Generated by Django 3.2.12 on 2022-03-22 11:21

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jsondataferret", "0002_jsondataferret"),
        ("indigo", "0013_assessmentresource"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pipeline",
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
                ("public_id", models.CharField(max_length=200, unique=True)),
                ("exists", models.BooleanField(default=False)),
                ("status_public", models.BooleanField(default=False)),
                (
                    "data_public",
                    django.contrib.postgres.fields.jsonb.JSONField(default=dict),
                ),
                (
                    "data_private",
                    django.contrib.postgres.fields.jsonb.JSONField(default=dict),
                ),
                (
                    "data_sandboxes",
                    django.contrib.postgres.fields.jsonb.JSONField(default=dict),
                ),
                ("full_text_search_private", models.TextField(default="")),
                (
                    "record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="jsondataferret.record",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
