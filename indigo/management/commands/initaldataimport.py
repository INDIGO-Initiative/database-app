import datetime
import json
import os
import re

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from jsondataferret import EVENT_MODE_REPLACE
from jsondataferret.pythonapi.newevent import NewEventData, newEvent
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
        parser.add_argument(
            "--disk", action="store_true", help="Store all data on disk for debug",
        )
        parser.add_argument(
            "--database", action="store_true", help="Store all data in DataBase",
        )

    def handle(self, *args, **options):
        self._import()
        if options["disk"]:
            self._write_to_disk()
        if options["database"]:
            self._write_to_database()

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
                file_name_bits = file_name.split(".")
                project_id = "INDIGO-" + "{:04d}".format(int(file_name_bits[0]))
                id_counter += 1
                self._import_project(file_name, project_id)

    def _import_project(self, file_name, project_id):
        print(file_name)
        in_dirname = os.path.join(settings.BASE_DIR, "import")
        # Open file
        in_workbook = openpyxl.load_workbook(
            os.path.join(in_dirname, file_name), read_only=True
        )
        data_worksheet = self._get_project_main_worksheet(in_workbook)
        source_worksheet = self._get_project_sources_worksheet(in_workbook)
        source_info = self._build_source_information_from_source_worksheet(
            source_worksheet
        )

        # out_source_dirname = os.path.join(settings.BASE_DIR, "import_out", "source")
        # os.makedirs(out_source_dirname, exist_ok=True)
        # with open(os.path.join(out_source_dirname, project_id + ".json"), "w") as fp:
        #   json.dump(source_info, fp)

        # DATA!
        project_data = {
            "outcome_funds": [],
            "delivery_locations": [],
            "sources": source_info["sources"],
            "service_provisions": [],
            "outcome_payment_commitments": [],
            "investments": [],
            "intermediary_services": [],
            "outcome_metrics": [],
            "results": [],
            "open_contracting_datas": [],
            "360giving_datas": [],
        }
        # name
        json_set_deep_value(project_data, "name/value", data_worksheet["F2"].value)
        # Stage
        stage = data_worksheet["C3"].value or ""
        if not stage:
            stage = data_worksheet["C2"].value or ""
            if stage.startswith("Stage: "):
                stage = stage[7:]
            # Seen in record 3
            if stage == "Completed":
                stage = "Complete"

        json_set_deep_value(project_data, "stage_development/value", stage)
        json_set_deep_value(
            project_data, "stage_development/status", DEFAULT_FIELD_LEVEL_STATUS
        )
        # Fund
        value = self._get_fixed_cell_value(data_worksheet, "F3")
        if value:
            fund_id = self._get_fund_id(value)
            source_ids = self._get_sources_for_cells(["F3"], source_info)
            project_data["outcome_funds"].append(
                {
                    "id": fund_id,
                    "source_ids": ",".join(source_ids),
                    "status": DEFAULT_FIELD_LEVEL_STATUS,
                }
            )
        # dates area .............
        dates_source_ids = []
        # Date Outcome Contract Signed .............
        value = self._get_fixed_cell(data_worksheet, "D5", source_info)
        if value:
            json_set_deep_value(
                project_data, "dates/outcomes_contract_signed/value", value["value"]
            )
            if value["source_id"]:
                dates_source_ids.append(value["source_id"])
            json_set_deep_value(
                project_data,
                "dates/outcomes_contract_signed/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Date service delivery started ....................
        value = self._get_fixed_cell(data_worksheet, "D8", source_info)
        if value:
            json_set_deep_value(
                project_data,
                "dates/start_date_of_service_provision/value",
                value["value"],
            )
            if value["source_id"]:
                dates_source_ids.append(value["source_id"])
            json_set_deep_value(
                project_data,
                "dates/start_date_of_service_provision/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # ........... Date Outcome Contract Signed and Date service delivery started  share the same source
        if dates_source_ids:
            json_set_deep_value(
                project_data, "dates/source_ids", ",".join(list(set(dates_source_ids))),
            )
        # Location
        value = self._get_fixed_cell(data_worksheet, "D6", source_info)
        if value:
            project_data["delivery_locations"] = [
                {
                    "location_name": {"value": value["value"]},
                    "status": DEFAULT_FIELD_LEVEL_STATUS,
                    "source_ids": value["source_id"],
                }
            ]
        # Service Provider(s)
        value = self._get_fixed_cell_value(data_worksheet, "D10")
        if value:
            bits = re.split(r";|,", value)
            org_ids = [self._get_org_id(x.strip()) for x in bits if x.strip()]
            source_ids = self._get_sources_for_cells(["D10"], source_info)
            for org_id in org_ids:
                if org_id:
                    project_data["service_provisions"].append(
                        {
                            "id": "serviceprovision"
                            + str(len(project_data["service_provisions"]) + 1),
                            "organisation_id": {"value": org_id},
                            "source_ids": ",".join(source_ids),
                            "status": DEFAULT_FIELD_LEVEL_STATUS,
                        }
                    )
        # Performance Manager
        value = self._get_fixed_cell_value(data_worksheet, "D12")
        if value:
            bits = re.split(r";|,", value)
            org_ids = [self._get_org_id(x.strip()) for x in bits if x.strip()]
            source_ids = self._get_sources_for_cells(["D12"], source_info)
            for org_id in org_ids:
                if org_id:
                    project_data["intermediary_services"].append(
                        {
                            "organisation_id": {"value": org_id},
                            "organisation_role_category": {
                                "value": "Performance management"
                            },
                            "source_ids": ",".join(source_ids),
                            "status": DEFAULT_FIELD_LEVEL_STATUS,
                        }
                    )
        # Technical Assistance Provider(s)
        value = self._get_fixed_cell_value(data_worksheet, "D13")
        if value:
            bits = re.split(r";|,", value)
            org_ids = [self._get_org_id(x.strip()) for x in bits if x.strip()]
            source_ids = self._get_sources_for_cells(["D13"], source_info)
            for org_id in org_ids:
                if org_id:
                    project_data["intermediary_services"].append(
                        {
                            "organisation_id": {"value": org_id},
                            "source_ids": ",".join(source_ids),
                            "status": DEFAULT_FIELD_LEVEL_STATUS,
                        }
                    )
        # Service Users Actively Engaged (in total)  - Target / Actual
        value_target = self._get_fixed_cell(data_worksheet, "D19", source_info)
        value_actual = self._get_fixed_cell(data_worksheet, "E19", source_info)
        if value_target and value_target["value"]:
            project_data["outcome_metrics"].append(
                {
                    "id": "outcomemetric1",
                    "source_ids": value_target["source_id"],
                    "targeted_number_of_service_users_or_beneficiaries_total": {
                        "value": value_target["value"]
                    },
                    "status": DEFAULT_FIELD_LEVEL_STATUS,
                }
            )
        elif value_actual and value_actual["value"]:
            # If no target data, but still actual data, we still want a blank target row
            project_data["outcome_metrics"].append(
                {"id": "outcomemetric1", "status": DEFAULT_FIELD_LEVEL_STATUS,}
            )
        if value_actual and value_actual["value"]:
            project_data["results"].append(
                {
                    # ID here is outcome id, so set it the same as above
                    "id": "outcomemetric1",
                    "source_ids": value_actual["source_id"],
                    "number_engaged_in_impact_bond": {"value": value_actual["value"]},
                    "status": DEFAULT_FIELD_LEVEL_STATUS,
                }
            )
        # purpose_and_classifications area
        purpose_and_classifications_source_ids = []
        # Policy Area ......
        value = self._get_fixed_cell(data_worksheet, "D7", source_info)
        if value:
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/policy_sector/value",
                value["value"],
            )
            if value["source_id"]:
                purpose_and_classifications_source_ids.append(value["source_id"])
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/policy_sector/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Intervention .......
        value = self._get_fixed_cell(data_worksheet, "G6", source_info)
        if value:
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/intervention/value",
                value["value"],
            )
            if value["source_id"]:
                purpose_and_classifications_source_ids.append(value["source_id"])
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/intervention/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # .... Policy Area  and Intervention share the same source ID
        if purpose_and_classifications_source_ids:
            json_set_deep_value(
                project_data,
                "purpose_and_classifications/source_ids",
                ",".join(list(set(purpose_and_classifications_source_ids))),
            )
        # Target Population Eligibility
        value = self._get_fixed_cell(
            data_worksheet,
            self._find_cell_below_a_set_label(
                "Target Population Eligibility", "G", 16, data_worksheet
            ),
            source_info,
        )
        if value:
            json_set_deep_value(
                project_data,
                "service_and_beneficiaries/target_population/value",
                value["value"],
            )
            # This is the only value we set in service_and_beneficiaries so just put source straight in
            json_set_deep_value(
                project_data,
                "service_and_beneficiaries/source_ids",
                value["source_id"],
            )
            json_set_deep_value(
                project_data,
                "service_and_beneficiaries/target_population/status",
                DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Comments and Notes
        value = self._get_fixed_cell(
            data_worksheet,
            self._find_cell_below_a_set_label(
                "Comments and Notes", "Q", 4, data_worksheet
            ),
            source_info,
        )
        if value:
            json_set_deep_value(project_data, "notes/value", value["value"])
            # no source id for this one
            json_set_deep_value(
                project_data, "notes/status", DEFAULT_FIELD_LEVEL_STATUS,
            )
        # Outcome Summary [ TABLE] -> Outcome Metrics [TABLE]
        start_column, start_row = self._find_cell_below_a_set_label_return_components(
            "Outcome", "C", 20, data_worksheet
        )
        table_data = self._get_table_data(
            start_column, start_row, "Total", ["C", "D", "K"], data_worksheet
        )
        for row_in in table_data:
            def_values = [row_in["data"]["C"], row_in["data"]["D"], row_in["data"]["K"]]
            row_out = {
                "id": "outcomemetric" + str(len(project_data["outcome_metrics"]) + 1),
                "definition": {"value": "\n".join([str(x) for x in def_values if x])},
                "source_ids": ",".join(
                    self._get_sources_for_cells(
                        [
                            "C" + str(row_in["row"]),
                            "D" + str(row_in["row"]),
                            "K" + str(row_in["row"]),
                        ],
                        source_info,
                    )
                ),
                "status": DEFAULT_FIELD_LEVEL_STATUS,
            }
            project_data["outcome_metrics"].append(row_out)
        # Outcome Payers/Commissioners [TABLE] -> Outcome Payment Commitments [TABLE]
        # TODO Currency?
        # But 33 Euros, 36 Dollars (USD I assume), 78 CHF, 89 Pounds or Dollars, not sure which.
        start_column, start_row = self._find_cell_below_a_set_label_return_components(
            [
                "Outcome Payers/Commissioners",
                "Outcome Payers/ Commissioners",
                "Outcomes Payers/Commissioners",
                "Commissioners",
            ],
            "C",
            20,
            data_worksheet,
        )
        table_data = self._get_table_data(
            start_column,
            start_row,
            ["Total", "Financial performance"],
            ["C", "D", "E"],
            data_worksheet,
        )
        for row_in in table_data:
            if row_in["data"]["C"]:
                org_id = self._get_org_id(row_in["data"]["C"])
                if org_id:
                    row_out = {
                        "organisation_id": {"value": org_id},
                        "source_ids": ",".join(
                            self._get_sources_for_cells(
                                [
                                    "C" + str(row_in["row"]),
                                    "D" + str(row_in["row"]),
                                    "E" + str(row_in["row"]),
                                ],
                                source_info,
                            )
                        ),
                        "status": DEFAULT_FIELD_LEVEL_STATUS,
                    }
                    if row_in["data"]["D"]:
                        row_out["maximum_potential_outcome_payment"] = {
                            "amount": {"value": row_in["data"]["D"]}
                        }
                    if row_in["data"]["E"]:
                        row_out["total_outcome_payments"] = {
                            "amount": {"value": row_in["data"]["E"]}
                        }
                    project_data["outcome_payment_commitments"].append(row_out)
        # Investors [TABLE] -> Investments [ TABLE]
        start_column, start_row = self._find_cell_below_a_set_label_return_components(
            ["Investors",], "R", 20, data_worksheet,
        )
        table_data = self._get_table_data(
            start_column, start_row, ["Total"], ["R", "S", "T", "U"], data_worksheet,
        )
        for row_in in table_data:
            if row_in["data"]["R"]:
                org_id = self._get_org_id(row_in["data"]["R"])
                if org_id:
                    row_out = {
                        "id": "investment" + str(len(project_data["investments"]) + 1),
                        "organisation_id": {"value": org_id},
                        "source_ids": ",".join(
                            self._get_sources_for_cells(
                                [
                                    "R" + str(row_in["row"]),
                                    "S" + str(row_in["row"]),
                                    "T" + str(row_in["row"]),
                                    "U" + str(row_in["row"]),
                                ],
                                source_info,
                            )
                        ),
                        "status": DEFAULT_FIELD_LEVEL_STATUS,
                    }
                    if row_in["data"]["S"]:
                        row_out["investment_type"] = {"value": row_in["data"]["S"]}
                    # TODO Column U, amount invested
                    project_data["investments"].append(row_out)
        # Investors - Total Row
        # TODO

        # Save in memory
        self.projects[project_id] = project_data

    def _get_project_main_worksheet(self, in_workbook):
        if "Data Template" in in_workbook:
            return in_workbook["Data Template"]
        elif "Master Template" in in_workbook:
            return in_workbook["Master Template"]
        elif "Data template" in in_workbook:
            return in_workbook["Data template"]
        elif "Project Template" in in_workbook:
            return in_workbook["Project Template"]
        elif "Template" in in_workbook:
            return in_workbook["Template"]
        else:
            raise Exception("Cant find main sheet!")

    def _get_project_sources_worksheet(self, in_workbook):
        if "Sources" in in_workbook:
            return in_workbook["Sources"]
        elif "Data Sources" in in_workbook:
            return in_workbook["Data Sources"]
        elif "Source" in in_workbook:
            return in_workbook["Source"]
        else:
            raise Exception("Cant find sources sheet!")

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
                json.dump(data, fp, indent=4)
        for id, data in self.funds.items():
            with open(os.path.join(out_funds_dirname, id + ".json"), "w") as fp:
                json.dump(data, fp, indent=4)
        for id, data in self.organisations.items():
            with open(os.path.join(out_organisations_dirname, id + ".json"), "w") as fp:
                json.dump(data, fp, indent=4)

    def _write_to_database(self):
        for id, data in self.funds.items():
            newEvent(
                [
                    NewEventData(
                        "fund", id, data, approved=True, mode=EVENT_MODE_REPLACE
                    )
                ],
                user=None,
                comment="Importer",
            )
        for id, data in self.organisations.items():
            newEvent(
                [
                    NewEventData(
                        "organisation", id, data, approved=True, mode=EVENT_MODE_REPLACE
                    )
                ],
                user=None,
                comment="Importer",
            )
        for id, data in self.projects.items():
            newEvent(
                [
                    NewEventData(
                        "project", id, data, approved=True, mode=EVENT_MODE_REPLACE
                    )
                ],
                user=None,
                comment="Importer",
            )

    def _get_fixed_cell_value(self, worksheet, cell_label):
        value = worksheet[cell_label].value
        if isinstance(value, datetime.datetime):
            value = value.strftime("%Y-%m")
        if isinstance(value, str) and value.strip() in [
            "N/A",
            "NA",
            "None",
            "Commissioner 2",
            "Commissioner 3",
            "Commissioner 4",
            "Commissioner 5",
            "Investor 2",
            "Investor 3",
            "Investor 4",
            "Investor 5",
            "Investor 6",
            "TEXT",
            "NUMBER",
        ]:
            return None
        if not value:
            return None
        return value

    def _get_fixed_cell(self, worksheet, cell_label, source_info):
        value = self._get_fixed_cell_value(worksheet, cell_label)
        if not value:
            return None

        source_id = None
        if cell_label.upper() in source_info["by_cell"]:
            source_id = source_info["by_cell"][cell_label.upper()]

        return {"value": value, "source_id": source_id}

    def _build_source_information_from_source_worksheet(self, source_worksheet):
        ########################### Interim data
        # some sheets (153) have added rows, so need to make sure we collect rows together and contact them by a new line
        data_by_cell_with_ranges = {}
        last_cell_address_value = None
        for row_idx in range(2, source_worksheet.max_row + 1):
            cell_address = source_worksheet["B" + str(row_idx)]
            cell_address_value = cell_address.value
            cell_source = source_worksheet["C" + str(row_idx)]
            cell_source_value = cell_source.value

            if cell_source_value and cell_source_value not in ["N/A", "NA"]:
                if cell_address_value:
                    last_cell_address_value = cell_address_value
                    data_by_cell_with_ranges[cell_address_value] = cell_source_value
                else:
                    data_by_cell_with_ranges[last_cell_address_value] += (
                        "\n" + cell_source_value
                    )

        ######################### Expand Cell Ranges
        data_by_cell = {}
        for key, value in data_by_cell_with_ranges.items():
            for key_single in self._expand_cell_range(key):
                data_by_cell[key_single] = value

        ######################### Make Unique Sources
        sources = []
        source_id = 1
        # Change to source ID's, creating the sources as we go
        sources_by_cell = {}
        for key, source_text in data_by_cell.items():
            existing_sources = [
                x for x in sources if x["name"]["value"] == source_text.strip()
            ]
            if not existing_sources:
                sources.append(
                    {
                        "id": "source" + str(source_id),
                        "name": {"value": source_text.strip(),},
                    }
                )
                source_id += 1
            existing_sources = [
                x for x in sources if x["name"]["value"] == source_text.strip()
            ]
            sources_by_cell[key.upper()] = existing_sources[0]["id"]

        ######################### Return
        return {
            "sources": sources,
            "by_cell": sources_by_cell,
        }

    def _find_cell_below_a_set_label(
        self, label_string_or_list, start_column, start_row, data_worksheet
    ):
        col, row = self._find_cell_below_a_set_label_return_components(
            label_string_or_list, start_column, start_row, data_worksheet
        )
        return col + str(row)

    def _find_cell_below_a_set_label_return_components(
        self, label_string_or_list, start_column, start_row, data_worksheet
    ):
        while start_row < 500:
            cell = data_worksheet[start_column + str(start_row)]
            if cell and cell.value:
                if (
                    isinstance(label_string_or_list, str)
                    and cell.value.strip() == label_string_or_list.strip()
                ):
                    return start_column, (start_row + 1)
                elif (
                    isinstance(label_string_or_list, list)
                    and isinstance(cell.value, str)
                    and cell.value.strip() in label_string_or_list
                ):
                    return start_column, (start_row + 1)
            start_row += 1
        raise Exception("CANT FIND " + str(label_string_or_list))

    def _get_table_data(
        self,
        start_column,
        start_row,
        end_label_string_or_list,
        columns_wanted,
        data_worksheet,
    ):
        out = []
        while start_row < 500:
            cell = data_worksheet[start_column + str(start_row)]
            if cell and cell.value:
                if (
                    isinstance(end_label_string_or_list, str)
                    and cell.value.strip() == end_label_string_or_list.strip()
                ) or (
                    isinstance(end_label_string_or_list, list)
                    and cell.value.strip() in end_label_string_or_list
                ):
                    return out
                else:
                    this_row_out = {"row": start_row, "data": {}}
                    for column in columns_wanted:
                        this_row_out["data"][column] = self._get_fixed_cell_value(
                            data_worksheet, column + str(start_row)
                        )
                    out.append(this_row_out)
            start_row += 1
        raise Exception("CANT FIND " + str(end_label_string_or_list))

    def _get_sources_for_cells(self, cells, sources_info):
        out = []
        for cell in cells:
            if (
                cell in sources_info["by_cell"]
                and sources_info["by_cell"][cell] not in out
            ):
                out.append(sources_info["by_cell"][cell])
        return out

    def _expand_cell_range(self, input):
        if "-" in input:
            input_bits = input.split("-")
            # MATCH THE FIRST PART
            input_0_match = re.match(r"^([A-Z]+)(\d+)", input_bits[0].strip())
            if not input_0_match:
                raise Exception("Could not parse " + input_bits[0])
            first_column = input_0_match.group(1)
            first_row = int(input_0_match.group(2))
            # MATCH THE SECOND PART
            # Sometimes people pass ranges like "C28-29"
            input_1_match_number_only = re.match(r"^(\d+)", input_bits[1].strip())
            if input_1_match_number_only:
                second_column = first_column
                second_row = int(input_1_match_number_only.group(0))
            else:
                input_1_match = re.match(r"^([A-Z]+)(\d+)", input_bits[1].strip())
                if not input_1_match:
                    raise Exception("Could not parse " + input_bits[1])
                second_column = input_1_match.group(1)
                second_row = int(input_1_match.group(2))
            # NOW CHECK MODE OF EXPANSION
            if first_column == second_column:
                out = []
                for idx in range(first_row, second_row + 1):
                    out.append(first_column + str(idx))
                return out
            else:
                raise Exception(
                    "Trying to expand cell range in a mode not supported yet " + input
                )
        else:
            return [input.strip()]

    def _get_org_id(self, org_name):
        # Data Cleaning
        if org_name.strip() in ["Inc."]:
            return None
        # Existing
        for key, value in self.organisations.items():
            if value["name"]["value"].strip().upper() == org_name.strip().upper():
                return key
        # New
        org_id = "ORG-" + "{:04d}".format(len(self.organisations) + 1)
        self.organisations[org_id] = {"name": {"value": org_name.strip()}}
        return org_id

    def _get_fund_id(self, fund_name):
        # Existing
        for key, value in self.funds.items():
            if value["name"]["value"].strip().upper() == fund_name.strip().upper():
                return key
        # New
        org_id = "FUND-" + "{:04d}".format(len(self.funds) + 1)
        self.funds[org_id] = {"name": {"value": fund_name.strip()}}
        return org_id


# c = Command()
# print(c._expand_cell_range("A5"))
# print(c._expand_cell_range("A5-A10"))
# print(c._expand_cell_range("A5-10"))
# exit(-1)
