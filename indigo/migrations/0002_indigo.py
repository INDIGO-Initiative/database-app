# Generated by Django 3.0.6 on 2020-06-01 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("indigo", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Indigo",
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
            ],
            options={
                "permissions": (("admin", "Admin - All admin tasks on Indigo data"),),
                "managed": False,
            },
        ),
    ]
