from django.core.management.base import BaseCommand

from indigo.models import Project


class Command(BaseCommand):
    help = "Change Project Id (This will break links; should be used carefully)"

    def add_arguments(self, parser):
        parser.add_argument("from")
        parser.add_argument("to")

    def handle(self, *args, **options):
        project = Project.objects.get(public_id=options["from"])
        if not project:
            raise Exception("Not Found")
        project.public_id = options["to"]
        project.save()
        project.record.public_id = options["to"]
        project.record.save()
