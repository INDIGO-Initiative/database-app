import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Organisation


class Command(BaseCommand):
    help = "Data Migration - Make all Organisations public"

    def add_arguments(self, parser):
        parser.add_argument("import_comment")

    def handle(self, *args, **options):

        writes = []
        for organisation in Organisation.objects.all():
            if organisation.data_private.get("status") != "PUBLIC":
                writes.append(
                    NewEventData(
                        organisation.record.type,
                        organisation.record,
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
