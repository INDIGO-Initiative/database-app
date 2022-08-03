# Generated by Django 3.2.12 on 2022-06-02 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indigo", "0015_alter_indigo_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assessmentresource",
            name="data_private",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="assessmentresource",
            name="data_public",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="assessmentresource",
            name="data_sandboxes",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="fund",
            name="data_private",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="fund",
            name="data_public",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="fund",
            name="data_sandboxes",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="data_private",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="data_public",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="organisation",
            name="data_sandboxes",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="pipeline",
            name="data_private",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="pipeline",
            name="data_public",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="pipeline",
            name="data_sandboxes",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="project",
            name="data_private",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="project",
            name="data_public",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="project",
            name="data_quality_report_counts_by_priority",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="project",
            name="data_sandboxes",
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="projectimport",
            name="data",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
