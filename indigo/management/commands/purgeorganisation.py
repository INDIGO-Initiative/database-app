from django.core.management.base import BaseCommand

from indigo.models import Organisation
from indigo.purge import purge_organisation


class Command(BaseCommand):
    help = "Purge a organisation from the database"

    def add_arguments(self, parser):
        parser.add_argument("organisation_id")

    def handle(self, *args, **options):
        organisation = Organisation.objects.get(public_id=options["organisation_id"])
        if organisation:
            purge_organisation(organisation)
            print("Done")
