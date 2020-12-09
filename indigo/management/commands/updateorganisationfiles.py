from django.core.management.base import BaseCommand

from indigo.files import update_public_files_for_organisation
from indigo.models import Organisation
from indigo.tasks import task_update_public_files_for_organisation


class Command(BaseCommand):
    help = "Update Organisation Files in our File Store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direct",
            action="store_true",
            help="Processes task directly instead of via queue and worker",
        )

    def handle(self, *args, **options):

        for organisation in Organisation.objects.all():
            if options["direct"]:
                update_public_files_for_organisation(organisation)
            else:
                task_update_public_files_for_organisation.delay(organisation.public_id)
