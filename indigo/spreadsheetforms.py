from copy import deepcopy

import jsondataferret
import jsonpointer

from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_FUND_LIST,
    TYPE_PROJECT_ORGANISATION_LIST,
    TYPE_PROJECT_PUBLIC_ID,
)


def convert_project_data_to_spreadsheetforms_data(project, public_only=False):
    # Get data
    # Note this will be data with extra records already added - that is fine
    data = deepcopy(project.data_public if public_only else project.data_private)

    # Add ID
    data["id"] = project.public_id

    # Done
    return data


def extract_edits_from_project_spreadsheet(record, import_json):
    # Remove record ID
    del import_json["id"]

    # Remove Org data from the data we save
    jsonpointer.set_pointer(
        import_json, TYPE_PROJECT_ORGANISATION_LIST["list_key"], None,
    )

    # Remove Fund data
    data_list = jsonpointer.resolve_pointer(
        import_json, TYPE_PROJECT_FUND_LIST["list_key"], default=None
    )
    if isinstance(data_list, list) and data_list:
        for data_item in data_list:
            # Maybe try and extract fund edits here later?
            # Remove Fund data from the data we save
            jsonpointer.set_pointer(
                data_item, TYPE_PROJECT_FUND_LIST["item_key_with_fund_details"], None,
            )

    # Return
    return [
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_PROJECT_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    ]


def convert_organisation_data_to_spreadsheetforms_data(organisation, public_only=False):
    # Get data
    data = deepcopy(
        organisation.data_public if public_only else organisation.data_private
    )

    # Add ID
    data["id"] = organisation.public_id

    # Done
    return data


def extract_edits_from_organisation_spreadsheet(record, import_json):
    # Remove record ID
    del import_json["id"]

    # Return
    return [
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_ORGANISATION_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    ]


def convert_fund_data_to_spreadsheetforms_data(fund, public_only=False):
    # Get data
    data = deepcopy(fund.data_public if public_only else fund.data_private)

    # Add ID
    data["id"] = fund.public_id

    # Done
    return data


def extract_edits_from_fund_spreadsheet(record, import_json):
    # Remove record ID
    del import_json["id"]

    # Return
    return [
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_FUND_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    ]


def convert_assessment_resource_data_to_spreadsheetforms_data(
    assessment_resource, public_only=False
):
    # Get data
    data = deepcopy(
        assessment_resource.data_public
        if public_only
        else assessment_resource.data_private
    )

    # Add ID
    data["id"] = assessment_resource.public_id

    # Done
    return data


def extract_edits_from_assessment_resource_spreadsheet(record, import_json):
    # Remove record ID
    del import_json["id"]

    # Return
    return [
        jsondataferret.pythonapi.newevent.NewEventData(
            TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
            record,
            import_json,
            mode=jsondataferret.EVENT_MODE_MERGE,
        )
    ]
