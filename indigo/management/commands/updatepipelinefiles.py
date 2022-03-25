from django.core.management.base import BaseCommand

from indigo.files import update_public_files_for_pipeline
from indigo.models import Pipeline
from indigo.tasks import task_update_public_files_for_pipeline


class Command(BaseCommand):
    help = "Update Pipeline Files in our File Store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direct",
            action="store_true",
            help="Processes task directly instead of via queue and worker",
        )

    def handle(self, *args, **options):

        for pipeline in Pipeline.objects.all():
            if options["direct"]:
                update_public_files_for_pipeline(pipeline)
            else:
                task_update_public_files_for_pipeline.delay(pipeline.public_id)
