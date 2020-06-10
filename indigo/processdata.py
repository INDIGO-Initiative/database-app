from collections import defaultdict

import jsondataferret
import jsonpointer

from indigo import (
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_ORGANISATION_LISTS_LIST,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import Organisation


def add_other_records_to_project(input_json, public_only=False):
    for organisation_list_data in TYPE_PROJECT_ORGANISATION_LISTS_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, organisation_list_data["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for data_item in data_list:
                org_id = jsonpointer.resolve_pointer(
                    data_item, organisation_list_data["item_id_key"], default=None
                )
                if org_id:
                    try:
                        organisation = Organisation.objects.get(public_id=org_id)
                        organisation_data = (
                            organisation.data_public
                            if public_only
                            else organisation.data_private
                        )
                        for data_key, org_key in organisation_list_data[
                            "item_to_org_map"
                        ].items():
                            jsonpointer.set_pointer(
                                data_item,
                                data_key,
                                jsonpointer.resolve_pointer(
                                    organisation_data, org_key, default=None
                                ),
                            )
                    except Organisation.DoesNotExist:
                        pass
    return input_json


def extract_edits_from_project_import(record, import_json):
    out = []
    organisation_data = defaultdict(list)

    ################### Look For Orgs
    for organisation_list_data in TYPE_PROJECT_ORGANISATION_LISTS_LIST:
        data_list = jsonpointer.resolve_pointer(
            import_json, organisation_list_data["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for data_item in data_list:
                # Extract Org data
                org_id = jsonpointer.resolve_pointer(
                    data_item, organisation_list_data["item_id_key"], default=None
                )
                if org_id:
                    org_data = {}
                    for data_key, org_key in organisation_list_data[
                        "item_to_org_map"
                    ].items():
                        jsonpointer.set_pointer(
                            org_data,
                            org_key,
                            jsonpointer.resolve_pointer(
                                data_item, data_key, default=None
                            ),
                        )
                        jsonpointer.set_pointer(
                            data_item, data_key, None,
                        )
                    organisation_data[org_id].append(org_data)

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
    for org_id, org_datas in organisation_data.items():
        try:
            organisation = Organisation.objects.get(public_id=org_id)
            # TODO check for mis-matching data
            # for now we assume its good and carry on
            edit_part = jsondataferret.pythonapi.newevent.NewEventData(
                TYPE_ORGANISATION_PUBLIC_ID,
                organisation.public_id,
                org_datas[0],
                mode=jsondataferret.EVENT_MODE_MERGE,
            )
            if edit_part.does_this_create_or_change_record():
                out.append(edit_part)
        except Organisation.DoesNotExist:
            pass  # TODO

    return out
