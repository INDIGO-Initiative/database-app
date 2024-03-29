# Generated by Django 3.1.5 on 2021-02-10 11:52

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indigo", "0011_project_data_quality_report_counts_by_priority"),
    ]

    operations = [
        migrations.CreateModel(
            name="Sandbox",
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
                ("title", models.TextField(default="")),
            ],
        ),
        migrations.AddField(
            model_name="fund",
            name="data_sandboxes",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="organisation",
            name="data_sandboxes",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="project",
            name="data_sandboxes",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]
