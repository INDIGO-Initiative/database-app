from django.core.management.base import BaseCommand

from indigo.models import Project
from indigo.purge import purge_project


class Command(BaseCommand):
    help = "Purge a project from the database"

    def add_arguments(self, parser):
        parser.add_argument("project_id")

    def handle(self, *args, **options):
        project = Project.objects.get(public_id=options["project_id"])
        if project:
            purge_project(project)
            print("Done")
