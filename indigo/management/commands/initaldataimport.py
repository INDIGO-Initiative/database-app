import datetime
import json
import os

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from spreadsheetforms.util import json_set_deep_value

DEFAULT_FIELD_LEVEL_STATUS = "PUBLIC"


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
            # LibreOffice creates lock files that start with a .
            if not file_name.startswith("."):
                project_id = "INDIGO-" + str(id_counter)
                id_counter += 1
                self._import_project(file_name, project_id)

    def _import_project(self, file_name, project_id):
        print(file_name)
        in_dirname = os.path.join(settings.BASE_DIR, "import")
        # Open file
        source_workbook = openpyxl.load_workbook(
            os.path.join(in_dirname, file_name), read_only=True
        )
        source_worksheet = self._get_project_main_worksheet(source_workbook)
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
        json_set_deep_value(
            project_data, "stage_development/status", DEFAULT_FIELD_LEVEL_STATUS
        )
        # Fund
        # TODO
        # Date Outcome Contract Signed
        value = self._get_value_as_string(source_worksheet, "D5")
        if value not in ["N/A"]:
            json_set_deep_value(
                project_data, "dates/outcomes_contract_signed/value", value
            )
            json_set_deep_value(
                project_data,
                "dates/outcomes_contract_signed/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Location
        # TODO
        # Policy Area
        value = source_worksheet["D7"].value
        if value not in ["N/A"]:
            # TODO correct case - have seen different cases in import spreadsheets
            json_set_deep_value(
                project_data, "purpose_and_classifications/policy_sector/value", value
            )
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/policy_sector/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Date service delivery started
        # TODO
        # Service Provider(s)
        # TODO
        # Performance Manager
        # TODO
        # Technical Assistance Provider(s)
        # TODO
        # Service Users Actively Engaged (in total)  - Target / Actual
        # TODO
        # Intervention
        # TODO
        # Target Population Eligibility
        # TODO
        # Comments and Notes
        # TODO
        # Outcome Summary [ TABLE] -> Outcome Metrics [TABLE]
        # TODO
        # Outcome Payers/Commissioners [TABLE] -> Outcome Payment Commitments [TABLE]
        # TODO
        # Investors [TABLE] -> Investments [ TABLE]
        # TODO
        # Investors - Total Row
        # TODO

        # Save in memory
        self.projects[project_id] = project_data

    def _get_value_as_string(self, worksheet, cellref):
        value = worksheet["D5"].value
        if isinstance(value, datetime.datetime):
            value = value.strftime("%Y-%m")
        return value

    def _get_project_main_worksheet(self, source_workbook):
        if "Data Template" in source_workbook:
            return source_workbook["Data Template"]
        elif "Master Template" in source_workbook:
            return source_workbook["Master Template"]

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
                json.dump(data, fp, indent=4)
