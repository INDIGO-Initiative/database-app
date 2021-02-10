TYPE_PROJECT_PUBLIC_ID = "project"
TYPE_ORGANISATION_PUBLIC_ID = "organisation"
TYPE_FUND_PUBLIC_ID = "fund"

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
    "/grants",
    "/technical_assistances",
    "/technical_assistance_details",
    "/documents",
    "/sources",
]

TYPE_PROJECT_ORGANISATION_REFERENCES_LIST = [
    {
        "list_key": "/service_provisions",
        "item_organisation_id_key": "/organisation_id/value",
    },
    {
        "list_key": "/outcome_payment_commitments",
        "item_organisation_id_key": "/organisation_id/value",
    },
    {"list_key": "/investments", "item_organisation_id_key": "/organisation_id/value"},
    {
        "list_key": "/intermediary_services",
        "item_organisation_id_key": "/organisation_id/value",
    },
    {
        "list_key": "/transactions",
        "item_organisation_id_key": "/sending_organisation_id/value",
    },
    {
        "list_key": "/transactions",
        "item_organisation_id_key": "/receiving_organisation_id/value",
    },
    {
        "list_key": "/grants",
        "item_organisation_id_key": "/recipient_organisation_id/value",
    },
    {
        "list_key": "/grants",
        "item_organisation_id_key": "/funding_organisation_id/value",
    },
    {
        "list_key": "/technical_assistances",
        "item_organisation_id_key": "/recipient_organisation_id/value",
    },
    {
        "list_key": "/technical_assistances",
        "item_organisation_id_key": "/funding_organisation_id/value",
    },
]

TYPE_PROJECT_ORGANISATION_COMMA_SEPARATED_REFERENCES_LIST = [
    {
        "list_key": "/results",
        "item_organisation_id_key": "/outcomes_validator_organisation_ids/value",
    },
    # TODO the comma separated orgs in outcome funds tab
]

TYPE_PROJECT_ORGANISATION_LIST = {
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

TYPE_PROJECT_SOURCES_REFERENCES = [
    "/stage_development/source_ids",
    "/dates/source_ids",
    "/overall_project_finance/source_ids",
    "/investment_details/source_ids",
    "/purpose_and_classifications/source_ids",
    "/service_and_beneficiaries/source_ids",
    "/changes_to_project_due_to_covid19/source_ids",
]

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

TYPE_PROJECT_SOURCES_REFERENCES_LIST = [
    {"list_key": "/outcome_funds", "item_source_ids_key": "/source_ids",},
    {"list_key": "/delivery_locations", "item_source_ids_key": "/source_ids",},
    {"list_key": "/service_provisions", "item_source_ids_key": "/source_ids",},
    {"list_key": "/outcome_payment_commitments", "item_source_ids_key": "/source_ids",},
    {"list_key": "/investments", "item_source_ids_key": "/source_ids",},
    {"list_key": "/intermediary_services", "item_source_ids_key": "/source_ids",},
    {"list_key": "/outcome_metrics", "item_source_ids_key": "/source_ids",},
    {"list_key": "/results", "item_source_ids_key": "/source_ids",},
    {"list_key": "/open_contracting_datas", "item_source_ids_key": "/source_ids",},
    {"list_key": "/360giving_datas", "item_source_ids_key": "/source_ids",},
    {"list_key": "/outcome_pricings", "item_source_ids_key": "/source_ids",},
    {"list_key": "/transactions", "item_source_ids_key": "/source_ids",},
    {"list_key": "/grants", "item_source_ids_key": "/source_ids",},
    {"list_key": "/technical_assistances", "item_source_ids_key": "/source_ids",},
    {
        "list_key": "/technical_assistance_details",
        "item_source_ids_key": "/source_ids",
    },
]

TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST = ["/contact", "/status"]
