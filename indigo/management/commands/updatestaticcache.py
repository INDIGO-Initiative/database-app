from django.core.management.base import BaseCommand

from indigo.staticcache import cache_json_schema_info, cache_spreadsheet_guide_info


class Command(BaseCommand):
    help = "Update Cached Information generated from static files: JSON Schema and Spreadsheet Guides"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        cache_json_schema_info()
        cache_spreadsheet_guide_info()
