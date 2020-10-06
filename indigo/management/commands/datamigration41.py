import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


class Command(BaseCommand):
    help = "Data Migration https://github.com/INDIGO-Initiative/database-app/issues/41"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        writes = []

        for project in Project.objects.all():
            print("Project " + project.public_id)

            if (
                project.data_private.get("stage_development", {}).get("value")
                == "Complete"
            ):

                print("Complete")

                old_value = (
                    project.data_private.get("service_and_beneficiaries", {})
                    .get("actual_number_service_users_or_beneficiaries_total", {})
                    .get("value")
                )

                print("Old Value: " + str(old_value))

                if not old_value:

                    new_value = 0
                    for row in project.data_private.get("results", []):
                        row_value = row.get("number_engaged_in_impact_bond", {}).get(
                            "value", 0
                        )
                        if isinstance(row_value, int) and row_value > 0:
                            new_value += row_value

                    print("New Value: " + str(new_value))

                    if new_value:
                        writes.append(
                            NewEventData(
                                project.record.type,
                                project.record,
                                {
                                    "service_and_beneficiaries": {
                                        "actual_number_service_users_or_beneficiaries_total": {
                                            "value": new_value,
                                            "status": "PUBLIC",
                                        }
                                    }
                                },
                                mode=jsondataferret.EVENT_MODE_MERGE,
                                approved=True,
                            )
                        )
            else:

                print("Not Complete")

                old_value = (
                    project.data_private.get("service_and_beneficiaries", {})
                    .get("targeted_number_service_users_or_beneficiaries_total", {})
                    .get("value")
                )

                print("Old Value: " + str(old_value))

                if not old_value:

                    new_value = 0
                    for row in project.data_private.get("outcome_metrics", []):
                        row_value = row.get(
                            "targeted_number_of_service_users_or_beneficiaries_total",
                            {},
                        ).get("value", 0)
                        if isinstance(row_value, int) and row_value > 0:
                            new_value += row_value

                    print("New Value: " + str(new_value))

                    if new_value:
                        writes.append(
                            NewEventData(
                                project.record.type,
                                project.record,
                                {
                                    "service_and_beneficiaries": {
                                        "targeted_number_service_users_or_beneficiaries_total": {
                                            "value": new_value,
                                            "status": "PUBLIC",
                                        }
                                    }
                                },
                                mode=jsondataferret.EVENT_MODE_MERGE,
                                approved=True,
                            )
                        )

        if writes:
            print("Saving")
            newEvent(
                writes,
                user=None,
                comment="Data Migration https://github.com/INDIGO-Initiative/database-app/issues/41",
            )
