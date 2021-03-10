import copy

import jsonpointer
import spreadsheetforms.util
from django.conf import settings

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_ORGANISATION_REFERENCES_LIST,
    TYPE_PROJECT_FUND_LIST,
    TYPE_PROJECT_ORGANISATION_COMMA_SEPARATED_REFERENCES_LIST,
    TYPE_PROJECT_ORGANISATION_LIST,
    TYPE_PROJECT_ORGANISATION_REFERENCES_LIST,
    TYPE_PROJECT_SOURCE_LIST,
    TYPE_PROJECT_SOURCES_REFERENCES,
    TYPE_PROJECT_SOURCES_REFERENCES_LIST,
)
from indigo.models import Fund, Organisation


def add_other_records_to_project(project_id, input_json, public_only=False):
    input_json = copy.deepcopy(input_json)

    # Add ID
    input_json["id"] = project_id

    # Organisations
    organisations = {}

    # Look up organisations and add to list (where we can't add more info in place)
    for config in TYPE_PROJECT_ORGANISATION_COMMA_SEPARATED_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_organisation_id_key"], default=None
                )
                if field_value and field_value.strip():
                    field_values = field_value.split(",")
                    for org_id in [
                        org_id.strip() for org_id in field_values if org_id.strip()
                    ]:
                        try:
                            organisation = Organisation.objects.get(
                                public_id=org_id, exists=True, status_public=True
                            )
                            organisations[organisation.public_id] = organisation
                        except Organisation.DoesNotExist:
                            pass

    # Look up Organisations, add to list and add more info in place
    for config in TYPE_PROJECT_ORGANISATION_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_organisation_id_key"], default=None
                )
                if field_value and field_value.strip():
                    try:
                        organisation = Organisation.objects.get(
                            public_id=field_value, exists=True, status_public=True
                        )
                        organisations[organisation.public_id] = organisation
                        organisation_data = (
                            organisation.data_public
                            if public_only
                            else organisation.data_private
                        )
                        spreadsheetforms.util.json_set_deep_value(
                            item,
                            "organisation_names" + config["item_organisation_id_key"],
                            jsonpointer.resolve_pointer(
                                organisation_data, "/name/value", default=None
                            ),
                        )
                    except Organisation.DoesNotExist:
                        pass

    # Put organisations list into organisations tab
    organisations_list = []
    for org_id, organisation in sorted(organisations.items(), key=lambda x: x[0]):
        organisation_data = (
            organisation.data_public if public_only else organisation.data_private
        )
        this_org_data = {}
        jsonpointer.set_pointer(
            this_org_data,
            TYPE_PROJECT_ORGANISATION_LIST["item_id_key"],
            organisation.public_id,
        )
        for data_key, org_key in TYPE_PROJECT_ORGANISATION_LIST[
            "item_to_org_map"
        ].items():
            # We don't use jsonpointer.set_pointer here because it can't cope with setting "deep" paths
            spreadsheetforms.util.json_set_deep_value(
                this_org_data,
                data_key[1:],
                jsonpointer.resolve_pointer(organisation_data, org_key, default=None),
            )
        organisations_list.append(this_org_data)
    jsonpointer.set_pointer(
        input_json, TYPE_PROJECT_ORGANISATION_LIST["list_key"], organisations_list
    )

    # Place funds in proper list place
    funds_list = jsonpointer.resolve_pointer(
        input_json, TYPE_PROJECT_FUND_LIST["list_key"], default=None
    )
    if isinstance(funds_list, list) and funds_list:
        for fund_row in funds_list:
            try:
                fund_id = jsonpointer.resolve_pointer(
                    fund_row, TYPE_PROJECT_FUND_LIST["item_id_key"], default=None
                )
                if fund_id:
                    fund = Fund.objects.get(public_id=fund_id)
                    fund_data = fund.data_public if public_only else fund.data_private
                    # We are going to add extra details to a "fund" dictionary, so set that as an empty dictionary now
                    # spreadsheetforms.util.json_set_deep_value won't do it for us, it has a bug when the existing key is None
                    jsonpointer.set_pointer(
                        fund_row,
                        TYPE_PROJECT_FUND_LIST["item_key_with_fund_details"],
                        {},
                    )
                    for data_key, fund_key in TYPE_PROJECT_FUND_LIST[
                        "item_to_fund_map"
                    ].items():
                        # We don't use jsonpointer.set_pointer here because it can't cope with setting "deep" paths
                        spreadsheetforms.util.json_set_deep_value(
                            fund_row,
                            data_key[1:],
                            jsonpointer.resolve_pointer(
                                fund_data, fund_key, default=None
                            ),
                        )
            except Fund.DoesNotExist:
                pass

    # Done
    return input_json


def add_other_records_to_fund(fund_id, input_json, public_only=False):
    input_json = copy.deepcopy(input_json)

    # Add ID
    input_json["id"] = fund_id

    # Look up Organisations, add more info in place
    for config in TYPE_FUND_ORGANISATION_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_organisation_id_key"], default=None
                )
                if field_value and field_value.strip():
                    try:
                        organisation = Organisation.objects.get(
                            public_id=field_value, exists=True, status_public=True
                        )
                        organisation_data = (
                            organisation.data_public
                            if public_only
                            else organisation.data_private
                        )
                        spreadsheetforms.util.json_set_deep_value(
                            item,
                            "organisation_names" + config["item_organisation_id_key"],
                            jsonpointer.resolve_pointer(
                                organisation_data, "/name/value", default=None
                            ),
                        )
                    except Organisation.DoesNotExist:
                        pass

    # Done
    return input_json


def does_organisation_data_contain_changes(organisation_model, new_data):
    for data_key, org_key in TYPE_PROJECT_ORGANISATION_LIST["item_to_org_map"].items():
        old_data_value = jsonpointer.resolve_pointer(
            organisation_model.record.cached_data, org_key, default=None
        )
        new_data_value = jsonpointer.resolve_pointer(new_data, data_key, default=None)
        if old_data_value != new_data_value:
            return True
    return False


def find_unique_organisation_ids_referenced_in_project_data(input_json):
    org_ids = []

    # For single keys
    for config in TYPE_PROJECT_ORGANISATION_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_organisation_id_key"], default=None
                )
                if field_value and field_value.strip():
                    org_ids.append(field_value)

    # For comma separated keys
    for config in TYPE_PROJECT_ORGANISATION_COMMA_SEPARATED_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_organisation_id_key"], default=None
                )
                if field_value and field_value.strip():
                    field_values = field_value.split(",")
                    org_ids.extend([id.strip() for id in field_values if id.strip()])

    return list(set(org_ids))


def filter_organisation_ids_that_do_not_exist_in_database(list_of_ids):
    """Takes list of public_ids of orgs, returns a list of those that do NOT exist in the database.
    Hint: feed find_unique_organisation_ids_referenced_in_project_data into this."""
    out = []
    for id in list_of_ids:
        try:
            Organisation.objects.get(public_id=id)
        except Organisation.DoesNotExist:
            out.append(id)
    return out


def find_unique_fund_ids_referenced_in_project_data(input_json):
    fund_ids = []

    # There is only one place funds are referenced in the project data
    data_list = jsonpointer.resolve_pointer(
        input_json, TYPE_PROJECT_FUND_LIST["list_key"], default=None
    )
    if isinstance(data_list, list) and data_list:
        for item in data_list:
            field_value = jsonpointer.resolve_pointer(
                item, TYPE_PROJECT_FUND_LIST["item_id_key"], default=None
            )
            field_value = str(field_value).strip() if field_value else None
            if field_value:
                fund_ids.append(field_value)

    return list(set(fund_ids))


def filter_fund_ids_that_do_not_exist_in_database(list_of_ids):
    """Takes list of public_ids of funds, returns a list of those that do NOT exist in the database.
    Hint: feed find_unique_fund_ids_referenced_in_project_data into this."""
    out = []
    for id in list_of_ids:
        try:
            Fund.objects.get(public_id=id)
        except Fund.DoesNotExist:
            out.append(id)
    return out


def check_project_data_for_source_errors(input_json):
    source_table_entries_that_are_not_used = []
    source_ids_referenced_that_are_not_in_sources_table = []
    source_ids_referenced = []
    source_ids_found = []

    # ----------------- Find all Source ID's referenced in data
    for key in TYPE_PROJECT_SOURCES_REFERENCES:
        field_value = jsonpointer.resolve_pointer(input_json, key, default="")
        if isinstance(field_value, str):
            for source_id in [s.strip() for s in field_value.strip().split(",")]:
                if source_id:
                    source_ids_referenced.append({"source_id": source_id})

    for config in TYPE_PROJECT_SOURCES_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_source_ids_key"], default=""
                )
                if field_value:
                    for source_id in [
                        s.strip() for s in field_value.strip().split(",")
                    ]:
                        if source_id:
                            source_ids_referenced.append({"source_id": source_id})

    # -------------------- Now look through source table
    source_list = jsonpointer.resolve_pointer(
        input_json, TYPE_PROJECT_SOURCE_LIST["list_key"], default=None
    )
    if isinstance(source_list, list) and source_list:
        # Look through source table looking for problems
        for source_item in source_list:
            source_id = jsonpointer.resolve_pointer(
                source_item, TYPE_PROJECT_SOURCE_LIST["item_id_key"], default=""
            )
            if source_id:
                source_id = source_id.strip()
                source_ids_found.append(source_id)
                # Is this source ID used? Add to list if not
                if (
                    len(
                        [
                            s
                            for s in source_ids_referenced
                            if s["source_id"] == source_id
                        ]
                    )
                    == 0
                ):
                    source_table_entries_that_are_not_used.append(
                        {"source_id": source_id}
                    )

    # ----------------- Finally find any sources referenced that aren't in source table
    for source_id_reference in source_ids_referenced:
        if (
            len([s for s in source_ids_found if s == source_id_reference["source_id"]])
            == 0
        ):
            source_ids_referenced_that_are_not_in_sources_table.append(
                source_id_reference
            )

    # ----------------- Done
    return (
        source_ids_referenced_that_are_not_in_sources_table,
        source_table_entries_that_are_not_used,
    )


def set_values_if_agnostic_on_assessment_resource_data(data):
    keys = [
        i["key"]
        for i in settings.JSONDATAFERRET_TYPE_INFORMATION.get(
            TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
        ).get("fields")
    ]
    for primary_key in keys:
        if (
            primary_key.endswith("/agnostic")
            and jsonpointer.resolve_pointer(data, primary_key, None) == "YES"
        ):
            primary_key_prefix = primary_key[: -len("/agnostic")]
            for secondary_key in keys:
                if secondary_key.startswith(primary_key_prefix):
                    jsonpointer.set_pointer(data, secondary_key, "YES")
    return data
