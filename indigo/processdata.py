from collections import defaultdict

import jsondataferret
import jsonpointer
import spreadsheetforms.util

from indigo import (
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_ORGANISATION_LIST,
    TYPE_PROJECT_ORGANISATION_REFERENCES_LIST,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import Organisation


def add_other_records_to_project(project_id, input_json, public_only=False):
    # Add ID
    input_json["id"] = project_id

    # Place organisations in proper list place
    organisations_list = []
    for org_id in find_unique_organisation_ids_referenced_in_project_data(input_json):
        try:
            organisation = Organisation.objects.get(public_id=org_id)
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
                    jsonpointer.resolve_pointer(
                        organisation_data, org_key, default=None
                    ),
                )
            organisations_list.append(this_org_data)
        except Organisation.DoesNotExist:
            pass
    jsonpointer.set_pointer(
        input_json, TYPE_PROJECT_ORGANISATION_LIST["list_key"], organisations_list
    )

    # Done
    return input_json


def extract_edits_from_project_import(record, import_json):
    out = []
    organisation_data = defaultdict(list)

    ################### Look For Orgs
    data_list = jsonpointer.resolve_pointer(
        import_json, TYPE_PROJECT_ORGANISATION_LIST["list_key"], default=None
    )
    if isinstance(data_list, list) and data_list:
        for data_item in data_list:
            # Extract Org data
            org_id = jsonpointer.resolve_pointer(
                data_item, TYPE_PROJECT_ORGANISATION_LIST["item_id_key"], default=None
            )
            if org_id:
                org_data = {}
                for data_key, org_key in TYPE_PROJECT_ORGANISATION_LIST[
                    "item_to_org_map"
                ].items():
                    # We don't use jsonpointer.set_pointer here because it can't cope with setting "deep" paths
                    spreadsheetforms.util.json_set_deep_value(
                        org_data,
                        org_key[1:],
                        jsonpointer.resolve_pointer(data_item, data_key, default=None),
                    )
                    jsonpointer.set_pointer(
                        data_item, data_key, None,
                    )
                organisation_data[org_id] = org_data

    ################### Now we have removed org data, create project edit
    out.append(
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_PROJECT_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    )

    ################### Create organisation edits
    for org_id, org_data in organisation_data.items():
        try:
            organisation = Organisation.objects.get(public_id=org_id)
            edit_part = jsondataferret.pythonapi.newevent.NewEventData(
                TYPE_ORGANISATION_PUBLIC_ID,
                organisation.public_id,
                org_data,
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            if edit_part.does_this_create_or_change_record():
                out.append(edit_part)
        except Organisation.DoesNotExist:
            pass  # TODO

    return out


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
                if field_value.strip():
                    org_ids.append(field_value)

    return list(set(org_ids))
