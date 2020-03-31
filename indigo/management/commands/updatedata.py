from django.core.management.base import BaseCommand

from indigo.updatedata import update_all_data


class Command(BaseCommand):
    help = "Update Data in our tables from main data"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        update_all_data()
