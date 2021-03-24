import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


class Command(BaseCommand):
    help = "Data Migration https://github.com/INDIGO-Initiative/indigo-data-standard/issues/26"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        writes = []

        for project in Project.objects.all():
            print("Project " + project.public_id)

            old_value = (
                project.data_private.get("overall_project_finance", {})
                .get("maximum_potential_outcome_payment", {})
                .get("value")
            )

            if old_value:

                print("Has Data " + str(old_value))

                old_status = (
                    project.data_private.get("overall_project_finance", {})
                    .get("maximum_potential_outcome_payment", {})
                    .get("status")
                )
                old_currency = (
                    project.data_private.get("overall_project_finance", {})
                    .get("total_investment_commitment", {})
                    .get("currency")
                    .get("value")
                )
                old_currency_status = (
                    project.data_private.get("overall_project_finance", {})
                    .get("total_investment_commitment", {})
                    .get("currency")
                    .get("status")
                )

                new_value = {
                    "overall_project_finance": {
                        "maximum_potential_outcome_payment_v2": {
                            "amount": {"value": old_value, "status": old_status},
                            "amount_usd": {"value": None, "status": None},
                            "currency": {
                                "value": old_currency,
                                "status": old_currency_status,
                            },
                        },
                        "maximum_potential_outcome_payment": None,
                    }
                }

                writes.append(
                    NewEventData(
                        project.record.type,
                        project.record,
                        new_value,
                        mode=jsondataferret.EVENT_MODE_MERGE,
                        approved=True,
                    )
                )

        if writes:
            print("Saving")
            newEvent(
                writes,
                user=None,
                comment="Data Migration https://github.com/INDIGO-Initiative/indigo-data-standard/issues/26",
            )
