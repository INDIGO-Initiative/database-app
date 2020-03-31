TYPE_PROJECT_PUBLIC_ID = "project"

JSONDATAFERRET_HOOKS = "indigo.jsondataferret"

_extra_value_components = ["value", "source", "status"]


TYPE_PROJECT_FIELD_LIST = [
    {"key": "/status", "title": "Status"},
]

for path, label in {
    "/project_name": "Project Name",
    "/fund_name": "Fund Name",
    "/launch_date": "Launch Date",
}.items():
    TYPE_PROJECT_FIELD_LIST.extend(
        [
            {"key": path + "/" + extra, "title": label + " (" + extra + ")"}
            for extra in _extra_value_components
        ]
    )

TYPE_PROJECT_FILTER_KEYS_LIST = ["/project_name", "/fund_name", "/launch_date"]
