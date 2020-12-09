from django.core.management.base import BaseCommand

from indigo.files import update_public_archive_files
from indigo.tasks import task_update_public_archive_files


class Command(BaseCommand):
    help = "Update Archive Files in our File Store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direct",
            action="store_true",
            help="Processes task directly instead of via queue and worker",
        )

    def handle(self, *args, **options):

        if options["direct"]:
            update_public_archive_files()
        else:
            task_update_public_archive_files.delay()
