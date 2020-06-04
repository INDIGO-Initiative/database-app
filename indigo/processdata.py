from collections import defaultdict

import jsondataferret
import jsonpointer

from indigo import TYPE_ORGANISATION_PUBLIC_ID, TYPE_PROJECT_PUBLIC_ID
from indigo.models import Organisation


def add_other_records_to_project(input_json, public_only=False):
    data_list = jsonpointer.resolve_pointer(input_json, "/outcome_funds", default=None)
    if isinstance(data_list, list) and data_list:
        for data_item in data_list:
            org_id = jsonpointer.resolve_pointer(
                data_item, "/organisation/id", default=None
            )
            if org_id:
                try:
                    organisation = Organisation.objects.get(public_id=org_id)
                    organisation_data = (
                        organisation.data_public
                        if public_only
                        else organisation.data_private
                    )
                    jsonpointer.set_pointer(
                        data_item,
                        "/organisation/name",
                        jsonpointer.resolve_pointer(
                            organisation_data, "/name", default=None
                        ),
                    )
                    jsonpointer.set_pointer(
                        data_item,
                        "/organisation/type",
                        jsonpointer.resolve_pointer(
                            organisation_data, "/type", default=None
                        ),
                    )
                except Organisation.DoesNotExist:
                    pass
    return input_json


def extract_edits_from_project_import(record, import_json):
    out = []
    organisation_data = defaultdict(list)

    data_list = jsonpointer.resolve_pointer(import_json, "/outcome_funds", default=None)
    if isinstance(data_list, list) and data_list:
        for data_item in data_list:
            # Extract Org data
            org_id = jsonpointer.resolve_pointer(
                data_item, "/organisation/id", default=None
            )
            if org_id:
                organisation_data[org_id].append(
                    {
                        "name": jsonpointer.resolve_pointer(
                            data_item, "/organisation/name", default=None
                        ),
                        "type": jsonpointer.resolve_pointer(
                            data_item, "/organisation/type", default=None
                        ),
                    }
                )
            # Finally remove org attributes
            jsonpointer.set_pointer(
                data_item, "/organisation/name", None,
            )
            jsonpointer.set_pointer(
                data_item, "/organisation/type", None,
            )

    out.append(
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_PROJECT_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    )

    for org_id, org_datas in organisation_data.items():
        try:
            organisation = Organisation.objects.get(public_id=org_id)

            out.append(
                jsondataferret.pythonapi.newevent.NewEventData(
                    TYPE_ORGANISATION_PUBLIC_ID,
                    organisation.public_id,
                    org_datas[0],
                    mode=jsondataferret.EVENT_MODE_MERGE,
                )
            )
        except Organisation.DoesNotExist:
            pass  # TODO

    return out
