import copy

import jsonpointer
from jsondataferret.models import Record, Type

import indigo.processdata
from indigo import (
    TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST,
    TYPE_PROJECT_FILTER_KEYS_LIST,
    TYPE_PROJECT_ORGANISATION_LISTS_LIST,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.models import Organisation, Project, ProjectIncludesOrganisation


def update_all_data():

    try:
        type_organisation = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        for organisation in Record.objects.filter(type=type_organisation):
            # update_projects=False because we are about to do that in next block anyway
            update_organisation(organisation, update_projects=False)
    except Type.DoesNotExist:
        pass

    # Because Projects can include Organisation data, we update projects last
    try:
        type_project = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        for project in Record.objects.filter(type=type_project):
            update_project(project, update_include_organisations=True)
    except Type.DoesNotExist:
        pass


def update_project(record, update_include_organisations=False):

    try:
        project = Project.objects.get(public_id=record.public_id)
    except Project.DoesNotExist:
        project = Project()
        project.public_id = record.public_id

    # record - this doesn't change after creation but we need to migrate old data
    project.record = record
    # Exists
    project.exists = record.cached_exists
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    project.status_public = record.cached_exists and record_status == "public"
    # Public Data
    if project.status_public:
        project.data_public = indigo.processdata.add_other_records_to_project(
            filter_values(
                record.cached_data,
                keys_with_own_status_subfield=TYPE_PROJECT_FILTER_KEYS_LIST,
                keys_always_remove=TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST,
            ),
            public_only=True,
        )
    else:
        project.data_public = {}
    # Private Data
    if record.cached_exists:
        project.data_private = indigo.processdata.add_other_records_to_project(
            record.cached_data, public_only=False
        )
    else:
        project.data_private = {}
    # Finally, Save
    project.save()

    if update_include_organisations:
        organisations = []
        for organisation_list_data in TYPE_PROJECT_ORGANISATION_LISTS_LIST:
            data_list = jsonpointer.resolve_pointer(
                record.cached_data, organisation_list_data["list_key"], default=None
            )
            if isinstance(data_list, list) and data_list:
                for data_item in data_list:
                    org_id = jsonpointer.resolve_pointer(
                        data_item, organisation_list_data["item_id_key"], default=None
                    )
                    if org_id:
                        try:
                            organisations.append(
                                Organisation.objects.get(public_id=org_id)
                            )
                        except Organisation.DoesNotExist:
                            pass
        # Save Organisations
        for organisation in organisations:
            try:
                project_includes_organisation = ProjectIncludesOrganisation.objects.get(
                    project=project, organisation=organisation
                )
            except ProjectIncludesOrganisation.DoesNotExist:
                project_includes_organisation = ProjectIncludesOrganisation()
                project_includes_organisation.organisation = organisation
                project_includes_organisation.project = project
            project_includes_organisation.in_current_data = True
            project_includes_organisation.save()
        # TODO also need to set in_current_data=False if org is removed
        # But at moment, how we use than variable it doesnt matter


def update_organisation(record, update_projects=False):

    try:
        organisation = Organisation.objects.get(public_id=record.public_id)
    except Organisation.DoesNotExist:
        organisation = Organisation()
        organisation.public_id = record.public_id

    # record - this doesn't change after creation but we need to migrate old data
    organisation.record = record
    # Exists
    organisation.exists = record.cached_exists
    # Status - at the moment we assume all org's are public
    organisation.status_public = record.cached_exists
    # Public data
    organisation.data_public = (
        filter_values(
            record.cached_data,
            keys_always_remove=TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST,
        )
        if organisation.status_public
        else {}
    )
    # Private Data
    organisation.data_private = record.cached_data if record.cached_exists else {}
    # Finally, Save
    organisation.save()

    if update_projects:
        for project_includes_organisation in ProjectIncludesOrganisation.objects.filter(
            in_current_data=True, organisation=organisation
        ):
            update_project(
                project_includes_organisation.project.record,
                update_include_organisations=False,
            )


def filter_values(data, keys_with_own_status_subfield=[], keys_always_remove=[]):
    data = copy.deepcopy(data)

    for key in keys_always_remove:
        jsonpointer.set_pointer(data, key, None)

    for key in keys_with_own_status_subfield:
        try:
            key_data = jsonpointer.resolve_pointer(data, key)
        except jsonpointer.JsonPointerException:
            # Data does not exist anyway, nothing to do!
            continue
        key_status = key_data.get("status", "") if isinstance(key_data, dict) else ""
        if isinstance(key_status, str) and key_status.strip().lower() == "public":
            # Remove Status key, it must be public, people don't need to see that.
            jsonpointer.set_pointer(data, key + "/status", None)
        else:
            # Remove all data!
            jsonpointer.set_pointer(data, key, None)

    return data
