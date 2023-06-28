TYPE_PROJECT_PUBLIC_ID = "project"
TYPE_ORGANISATION_PUBLIC_ID = "organisation"
TYPE_FUND_PUBLIC_ID = "fund"
TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID = "assessment_resource"
TYPE_PIPELINE_PUBLIC_ID = "pipeline"
TYPE_JOINING_UP_INITIATIVE_PUBLIC_ID = "joining_up_initiative"

ID_PREFIX_BY_TYPE = {
    "project": "INDIGO-POJ-",
    "organisation": "INDIGO-ORG-",
    "fund": "INDIGO-FUND-",
    "assessment_resource": "INDIGO-ARES-",
    "pipeline": "INDIGO-PL-",
    "joining_up_initiative": "INDIGO-JUI-",
}

JSONDATAFERRET_HOOKS = "indigo.jsondataferret"

TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST = [
    "/status",
]

TYPE_PROJECT_FILTER_LISTS_LIST = [
    "/outcome_funds",
    "/delivery_locations",
    "/service_provisions",
    "/outcome_payment_commitments",
    "/investments",
    "/intermediary_services",
    "/outcome_metrics",
    "/results",
    "/open_contracting_datas",
    "/360giving_datas",
    "/outcome_pricings",
    "/transactions",
    "/technical_assistances",
    "/technical_assistance_details",
    "/documents",
    "/sources",
    "/outcome_payment_plans",
    "/outcome_payments",
]

TYPE_PROJECT_AND_PIPELINE_ORGANISATION_LIST = {
    # The key in the whole project data where we look for the list
    "list_key": "/organisations",
    # In each item in the list, the key where we find the public ID of the organisation
    "item_id_key": "/id",
    # If the item in the list has other org fields that we should pull out of the org record, put them here
    # key is key in item in list: value is key in organisation record (this should always start with a slash )
    "item_to_org_map": {
        "/name/value": "/name/value",
        "/org-ids/company/value": "/org-ids/company/value",
        "/org-ids/charity/value": "/org-ids/charity/value",
        "/org-ids/other/value": "/org-ids/other/value",
        "/contact/name/value": "/contact/name/value",
        "/contact/email/value": "/contact/email/value",
        "/website/value": "/website/value",
        "/address/value": "/address/value",
        "/postcode/value": "/postcode/value",
        "/country/value": "/country/value",
    },
}

TYPE_PROJECT_SOURCE_LIST = {
    # The key in the whole project data where we look for the list
    "list_key": "/sources",
    # In each item in the list, the key where we find the ID of the source
    "item_id_key": "/id",
}
TYPE_PROJECT_FUND_LIST = {
    # The key in the whole project data where we look for the list
    "list_key": "/outcome_funds",
    # In each item in the list, the key where we find the ID of the source
    "item_id_key": "/id",
    # key to remove from each item when importing
    "item_key_with_fund_details": "/fund",
    # If the item in the list has other fund fields that we should pull out of the fund record, put them here
    # key is key in item in list: value is key in fund record (this should always start with a slash )
    "item_to_fund_map": {
        "/fund/name/value": "/name/value",
        "/fund/identifier_scheme/value": "/identifier_scheme/value",
        "/fund/identifier/value": "/identifier/value",
        "/fund/country/value": "/country/value",
    },
    # TODO add organisations to above mapping in some way, but it's more complex as we have to convert list <-> comma seperated string
}

TYPE_PROJECT_MAP_VALUES_STAGE_DEVELOPMENT = {
    "Completed ": "Complete",
    "Implementation ": "Implementation",
}

TYPE_PROJECT_MAP_VALUES_PURPOSE_AND_CLASSIFICATIONS_POLICY_SECTOR = {
    "Homelessness ": "Homelessness",
    "Poverty": "Poverty reduction",
    "Education and Early Years": "Education",
    "Education and early years": "Education",
    "Employment": "Employment and training",
    "Health and wellbeing": "Health",
    "Health & wellbeing": "Health",
    "Maternal and child health": "Health",
    "Children development": "Child and family welfare",
    "Child & family welfare": "Child and family welfare",
}

TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST = [
    "/status",
    # The following are old fields that were removed. To make sure old data is not included in API data, remove them.
    "/org-ids/company",
    "/org-ids/charity",
    "/org-ids/other",
]

TYPE_FUND_ALWAYS_FILTER_KEYS_LIST = [
    "/status",
]


TYPE_FUND_FILTER_LISTS_LIST = [
    "/documents",
]


TYPE_PIPELINE_ALWAYS_FILTER_KEYS_LIST = [
    "/status",
]

TYPE_PIPELINE_FILTER_LISTS_LIST = [
    "/delivery_locations",
    "/service_provisions",
    "/outcome_payment_commitments",
    "/investments",
    "/intermediary_services",
    "/outcome_metrics",
    "/documents",
    "/sources",
]

TYPE_JOINING_UP_INITIATIVE_ALWAYS_FILTER_KEYS_LIST = [
    "/status",
]
