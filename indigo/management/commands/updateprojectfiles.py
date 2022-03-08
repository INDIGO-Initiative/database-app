from django.core.management.base import BaseCommand

from indigo.files import (
    update_data_quality_report_file_for_all_projects,
    update_public_files_for_project,
)
from indigo.models import Project
from indigo.tasks import (
    task_update_data_quality_report_file_for_all_projects,
    task_update_public_files_for_project,
)


class Command(BaseCommand):
    help = "Update Project Files in our File Store"

    def add_arguments(self, parser):
        parser.add_argument(
            "--direct",
            action="store_true",
            help="Processes task directly instead of via queue and worker",
        )

    def handle(self, *args, **options):

        for project in Project.objects.all():
            if options["direct"]:
                update_public_files_for_project(project)
            else:
                task_update_public_files_for_project.delay(project.public_id)

        if options["direct"]:
            update_data_quality_report_file_for_all_projects()
        else:
            task_update_data_quality_report_file_for_all_projects.delay()
