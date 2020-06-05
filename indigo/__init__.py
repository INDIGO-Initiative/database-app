TYPE_PROJECT_PUBLIC_ID = "project"
TYPE_ORGANISATION_PUBLIC_ID = "organisation"

JSONDATAFERRET_HOOKS = "indigo.jsondataferret"

TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST = ["/status"]
TYPE_PROJECT_FILTER_KEYS_LIST = ["/project_name", "/fund_name", "/launch_date"]
TYPE_PROJECT_ORGANISATION_LISTS_LIST = [
    {
        "list_key": "/outcome_funds",
        "item_id_key": "/organisation/id",
        "item_to_org_map": {
            "/organisation/name": "/name",
            "/organisation/type": "/type",
        },
    }
]

TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST = ["/contact"]
