import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Fund


class Command(BaseCommand):
    help = "Data Migration - Make all Funds public"

    def add_arguments(self, parser):
        parser.add_argument("import_comment")

    def handle(self, *args, **options):

        writes = []
        for fund in Fund.objects.all():
            if fund.data_private.get("status") != "PUBLIC":
                writes.append(
                    NewEventData(
                        fund.record.type,
                        fund.record,
                        {"status": "PUBLIC"},
                        mode=jsondataferret.EVENT_MODE_MERGE,
                        approved=True,
                    )
                )
        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment=options["import_comment"],
            )
