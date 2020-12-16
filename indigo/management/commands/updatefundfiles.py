from django.core.management.base import BaseCommand

from indigo.files import update_public_files_for_fund
from indigo.models import Fund
from indigo.tasks import task_update_public_files_for_fund


class Command(BaseCommand):
    help = "Update Fund Files in our File Store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direct",
            action="store_true",
            help="Processes task directly instead of via queue and worker",
        )

    def handle(self, *args, **options):

        for fund in Fund.objects.all():
            if options["direct"]:
                update_public_files_for_fund(fund)
            else:
                task_update_public_files_for_fund.delay(fund.public_id)
