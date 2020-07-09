import json
import os

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from spreadsheetforms.util import json_set_deep_value


class Command(BaseCommand):
    help = "Initial Data Import"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projects = {}
        self.organisations = {}
        self.funds = {}

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        self._import()
        self._write_to_disk()

    def _import(self):
        in_dirname = os.path.join(settings.BASE_DIR, "import")
        file_names = [
            f
            for f in os.listdir(in_dirname)
            if os.path.isfile(os.path.join(in_dirname, f))
        ]
        id_counter = 1
        for file_name in file_names:
            project_id = "INDIGO-" + str(id_counter)
            id_counter += 1
            self._import_project(file_name, project_id)

    def _import_project(self, file_name, project_id):
        in_dirname = os.path.join(settings.BASE_DIR, "import")
        # Open file
        source_workbook = openpyxl.load_workbook(
            os.path.join(in_dirname, file_name), read_only=True
        )
        source_worksheet = source_workbook["Data Template"]
        # DATA!
        project_data = {}
        # name
        json_set_deep_value(project_data, "name/value", source_worksheet["F2"].value)
        # Stage
        stage = source_worksheet["C3"].value or ""
        if not stage:
            stage = source_worksheet["C2"].value or ""
            if stage.startswith("Stage: "):
                stage = stage[7:]
        json_set_deep_value(project_data, "stage_development/value", stage)
        # Save in memory
        self.projects[project_id] = project_data

    def _write_to_disk(self):
        out_projects_dirname = os.path.join(settings.BASE_DIR, "import_out", "projects")
        out_funds_dirname = os.path.join(settings.BASE_DIR, "import_out", "funds")
        out_organisations_dirname = os.path.join(
            settings.BASE_DIR, "import_out", "organisations"
        )
        os.makedirs(out_projects_dirname, exist_ok=True)
        os.makedirs(out_funds_dirname, exist_ok=True)
        os.makedirs(out_organisations_dirname, exist_ok=True)
        for id, data in self.projects.items():
            with open(os.path.join(out_projects_dirname, id + ".json"), "w") as fp:
                json.dump(data, fp)
        for id, data in self.funds.items():
            with open(os.path.join(out_funds_dirname, id + ".json"), "w") as fp:
                json.dump(data, fp)
        for id, data in self.organisations.items():
            with open(os.path.join(out_organisations_dirname, id + ".json"), "w") as fp:
                json.dump(data, fp)
