import copy

import jsonpointer
from django.conf import settings
from jsondataferret.models import Record, Type

import indigo.processdata
from indigo import (
    TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID,
    TYPE_FUND_ALWAYS_FILTER_KEYS_LIST,
    TYPE_FUND_FILTER_LISTS_LIST,
    TYPE_FUND_PUBLIC_ID,
    TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST,
    TYPE_ORGANISATION_PUBLIC_ID,
    TYPE_PIPELINE_ALWAYS_FILTER_KEYS_LIST,
    TYPE_PIPELINE_FILTER_LISTS_LIST,
    TYPE_PIPELINE_PUBLIC_ID,
    TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST,
    TYPE_PROJECT_FILTER_LISTS_LIST,
    TYPE_PROJECT_MAP_VALUES_PURPOSE_AND_CLASSIFICATIONS_POLICY_SECTOR,
    TYPE_PROJECT_MAP_VALUES_STAGE_DEVELOPMENT,
    TYPE_PROJECT_PUBLIC_ID,
)
from indigo.dataqualityreport import DataQualityReportForProject
from indigo.models import (
    AssessmentResource,
    Fund,
    Organisation,
    Pipeline,
    Project,
    ProjectIncludesFund,
    ProjectIncludesOrganisation,
    Sandbox,
)


def update_all_data():

    try:
        type_assessment_resource = Type.objects.get(
            public_id=TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID
        )
        for assessment_resource in Record.objects.filter(type=type_assessment_resource):
            update_assessment_resource(assessment_resource)
    except Type.DoesNotExist:
        pass

    try:
        type_organisation = Type.objects.get(public_id=TYPE_ORGANISATION_PUBLIC_ID)
        for organisation in Record.objects.filter(type=type_organisation):
            # update_projects=False because we are about to do that in next block anyway
            update_organisation(organisation, update_projects=False)
    except Type.DoesNotExist:
        pass

    # Because Funds refer to Organisations do them after
    try:
        type_fund = Type.objects.get(public_id=TYPE_FUND_PUBLIC_ID)
        for fund in Record.objects.filter(type=type_fund):
            # update_projects=False because we are about to do that in next block anyway
            update_fund(fund, update_projects=False)
    except Type.DoesNotExist:
        pass

    # Because Projects can include Organisation & Fund data, we update projects after
    try:
        type_project = Type.objects.get(public_id=TYPE_PROJECT_PUBLIC_ID)
        for project in Record.objects.filter(type=type_project):
            update_project(
                project, update_include_organisations=True, update_include_funds=True
            )
            update_project_low_priority(project)
    except Type.DoesNotExist:
        pass

    # Because Pipeline can include Organisation & Project data, we update Pipeline after
    try:
        type_pipeline = Type.objects.get(public_id=TYPE_PIPELINE_PUBLIC_ID)
        for pipeline in Record.objects.filter(type=type_pipeline):
            update_pipeline(pipeline)
    except Type.DoesNotExist:
        pass


def update_project(
    record, update_include_organisations=False, update_include_funds=False
):

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
    # Data
    data = map_project_values(record.cached_data)
    # Public and Sandbox Data
    if project.status_public:
        # Public Data
        public_filter_values_data = filter_values(
            data,
            keys_with_own_status_subfield=settings.JSONDATAFERRET_TYPE_INFORMATION.get(
                "project"
            ).get("filter_keys"),
            keys_always_remove=TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST,
            lists_with_items_with_own_status_subfield=TYPE_PROJECT_FILTER_LISTS_LIST,
        )
        project.data_public = indigo.processdata.add_other_records_to_project(
            record.public_id, public_filter_values_data, public_only=True,
        )
        # Sandbox Data
        project.data_sandboxes = {}
        for sandbox in Sandbox.objects.all():
            sandbox_filter_values_data = filter_values(
                data,
                keys_with_own_status_subfield=settings.JSONDATAFERRET_TYPE_INFORMATION.get(
                    "project"
                ).get(
                    "filter_keys"
                ),
                keys_always_remove=TYPE_PROJECT_ALWAYS_FILTER_KEYS_LIST,
                lists_with_items_with_own_status_subfield=TYPE_PROJECT_FILTER_LISTS_LIST,
                sandbox=sandbox,
            )
            if sandbox_filter_values_data != public_filter_values_data:
                project.data_sandboxes[
                    sandbox.public_id
                ] = indigo.processdata.add_other_records_to_project(
                    record.public_id, sandbox_filter_values_data, public_only=True,
                )
    else:
        project.data_public = {}
        project.data_sandboxes = {}
    # Private Data
    if record.cached_exists:
        project.data_private = indigo.processdata.add_other_records_to_project(
            record.public_id, data, public_only=False
        )
    else:
        project.data_private = {}
    # social_investment_prototype (BII)
    project.social_investment_prototype = (
        jsonpointer.resolve_pointer(
            project.data_public, "/social_investment_prototype/value", "NO"
        )
        == "YES"
    )
    # Finally, Save
    project.save()

    if update_include_organisations:
        organisations = []
        for (
            org_id
        ) in indigo.processdata.find_unique_organisation_ids_referenced_in_project_data(
            record.cached_data
        ):
            try:
                organisations.append(Organisation.objects.get(public_id=org_id))
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

    if update_include_funds:
        funds = []
        for (
            fund_id
        ) in indigo.processdata.find_unique_fund_ids_referenced_in_project_data(
            record.cached_data
        ):
            try:
                funds.append(Fund.objects.get(public_id=fund_id))
            except Fund.DoesNotExist:
                pass
        # Save Funds
        for fund in funds:
            try:
                project_includes_fund = ProjectIncludesFund.objects.get(
                    project=project, fund=fund
                )
            except ProjectIncludesFund.DoesNotExist:
                project_includes_fund = ProjectIncludesFund()
                project_includes_fund.fund = fund
                project_includes_fund.project = project
            project_includes_fund.in_current_data = True
            project_includes_fund.save()
        # TODO also need to set in_current_data=False if fund is removed
        # But at moment, how we use than variable it doesnt matter


def update_project_low_priority(record):
    # This should only ever be called after update_project()
    # so we don't have to deal with the case that the object does not exist.
    project = Project.objects.get(public_id=record.public_id)
    # Data Quality Report
    if record.cached_exists:
        dqr = DataQualityReportForProject(record.cached_data)
        project.data_quality_report_counts_by_priority = (
            dqr.get_count_errors_in_priority_levels()
        )
    else:
        project.data_quality_report_counts_by_priority = {}
    # Finally, Save
    project.save()


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
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    organisation.status_public = record.cached_exists and record_status == "public"
    # Public data
    if organisation.status_public:
        organisation.data_public = filter_values(
            record.cached_data,
            keys_always_remove=TYPE_ORGANISATION_ALWAYS_FILTER_KEYS_LIST,
        )
    else:
        organisation.data_public = {}
    # Private Data
    organisation.data_private = record.cached_data if record.cached_exists else {}
    # Full Text Search
    organisation.full_text_search_private = record.public_id
    for field in [
        i.get("key")
        for i in settings.JSONDATAFERRET_TYPE_INFORMATION.get("organisation").get(
            "fields"
        )
    ]:
        organisation.full_text_search_private += " " + str(
            jsonpointer.resolve_pointer(organisation.data_private, field, default="")
        )
    # Finally, Save
    organisation.save()

    if update_projects:
        for project_includes_organisation in ProjectIncludesOrganisation.objects.filter(
            in_current_data=True, organisation=organisation
        ):
            update_project(
                project_includes_organisation.project.record,
                update_include_organisations=False,
                update_include_funds=False,
            )


def update_fund(record, update_projects=False):

    try:
        fund = Fund.objects.get(public_id=record.public_id)
    except Fund.DoesNotExist:
        fund = Fund()
        fund.public_id = record.public_id
        fund.record = record

    # Exists
    fund.exists = record.cached_exists
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    fund.status_public = record.cached_exists and record_status == "public"
    # Public data
    if fund.status_public:
        fund.data_public = indigo.processdata.add_other_records_to_fund(
            fund.public_id,
            filter_values(
                record.cached_data,
                keys_always_remove=TYPE_FUND_ALWAYS_FILTER_KEYS_LIST,
                lists_with_items_with_own_status_subfield=TYPE_FUND_FILTER_LISTS_LIST,
            ),
            True,
        )
    else:
        fund.data_public = {}
    # Private Data
    fund.data_private = record.cached_data if record.cached_exists else {}
    # Finally, Save
    fund.save()

    if update_projects:
        for project_includes_fund in ProjectIncludesFund.objects.filter(
            in_current_data=True, fund=fund
        ):
            update_project(
                project_includes_fund.project.record,
                update_include_funds=False,
                update_include_organisations=False,
            )


def update_pipeline(record):

    try:
        pipeline = Pipeline.objects.get(public_id=record.public_id)
    except Pipeline.DoesNotExist:
        pipeline = Pipeline()
        pipeline.public_id = record.public_id
        pipeline.record = record

    # Exists
    pipeline.exists = record.cached_exists
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    pipeline.status_public = record.cached_exists and record_status == "public"
    # Public data
    if pipeline.status_public:
        pipeline.data_public = indigo.processdata.add_other_records_to_pipeline(
            record.public_id,
            filter_values(
                record.cached_data,
                keys_with_own_status_subfield=settings.JSONDATAFERRET_TYPE_INFORMATION.get(
                    "pipeline"
                ).get(
                    "filter_keys"
                ),
                keys_always_remove=TYPE_PIPELINE_ALWAYS_FILTER_KEYS_LIST,
                lists_with_items_with_own_status_subfield=TYPE_PIPELINE_FILTER_LISTS_LIST,
            ),
            public_only=True,
        )

    else:
        pipeline.data_public = {}
    # Private Data
    pipeline.data_private = (
        indigo.processdata.add_other_records_to_pipeline(
            record.public_id, record.cached_data, public_only=False
        )
        if record.cached_exists
        else {}
    )
    # Finally, Save
    pipeline.save()


def update_assessment_resource(record):

    try:
        assessment_resource = AssessmentResource.objects.get(public_id=record.public_id)
    except AssessmentResource.DoesNotExist:
        assessment_resource = AssessmentResource()
        assessment_resource.public_id = record.public_id
        assessment_resource.record = record

    # Exists
    assessment_resource.exists = record.cached_exists
    # Status
    record_status = (
        record.cached_data.get("status", "").strip().lower()
        if isinstance(record.cached_data.get("status", ""), str)
        else ""
    )
    assessment_resource.status_public = (
        record.cached_exists and record_status == "public"
    )
    # Public data
    if assessment_resource.status_public:
        # set_values_if_agnostic_on_assessment_resource_data is also called in extract_edits_from_assessment_resource_spreadsheet
        # So why do we need it here?
        # There is old imported data that may not have these values set correctly, and we call it here to correct them
        assessment_resource.data_public = indigo.processdata.set_values_if_agnostic_on_assessment_resource_data(
            record.cached_data
        )
    else:
        assessment_resource.data_public = {}
    # Private Data
    assessment_resource.data_private = (
        record.cached_data if record.cached_exists else {}
    )
    # Finally, Save
    assessment_resource.save()


def filter_values(
    data,
    keys_with_own_status_subfield=[],
    keys_always_remove=[],
    lists_with_items_with_own_status_subfield=[],
    sandbox=None,
):
    data = copy.deepcopy(data)

    # We always remove some keys
    for key in keys_always_remove:
        try:
            jsonpointer.set_pointer(data, key, None)
        except jsonpointer.JsonPointerException:
            # Data does not exist anyway, nothing to do!
            continue

    # Some single values (or groups of single values) might be removed, based on a status field.
    for key in keys_with_own_status_subfield:
        try:
            key_data = jsonpointer.resolve_pointer(data, key)
        except jsonpointer.JsonPointerException:
            # Data does not exist anyway, nothing to do!
            continue
        if is_block_status_public_or_in_sandbox(key_data, sandbox):
            # Remove Status key, it must be public, people don't need to see that.
            jsonpointer.set_pointer(data, key + "/status", None)
            if jsonpointer.resolve_pointer(data, key + "/sandboxes", None):
                jsonpointer.set_pointer(data, key + "/sandboxes", None)
        else:
            # Remove all data!
            jsonpointer.set_pointer(data, key, None)

    # Some lists have items with a status field, which we might remove
    for list_key in lists_with_items_with_own_status_subfield:
        try:
            old_list = jsonpointer.resolve_pointer(data, list_key)
        except jsonpointer.JsonPointerException:
            # Data does not exist anyway, nothing to do!
            continue
        if isinstance(old_list, list) and old_list:
            new_list = []
            for item in old_list:
                if is_block_status_public_or_in_sandbox(item, sandbox):
                    del item["status"]
                    if "sandboxes" in item:
                        del item["sandboxes"]
                    # We temporarily are removing source ID's and treating as private data
                    if "source_ids" in item:
                        del item["source_ids"]
                    new_list.append(item)
            jsonpointer.set_pointer(data, list_key, new_list)

    # Done
    return data


def is_block_status_public_or_in_sandbox(data, sandbox=None):
    # Sanity Check Incoming Data
    if not isinstance(data, dict):
        return False
    # Status Public?
    key_status = data.get("status", "")
    if isinstance(key_status, str) and key_status.strip().lower() == "public":
        return True
    # In correct sandbox?
    if (
        sandbox
        and isinstance(key_status, str)
        and key_status.strip().lower() == "sandbox"
    ):
        sandboxes = [
            i.strip() for i in data.get("sandboxes", "").split(",") if i.strip()
        ]
        if sandbox.public_id in sandboxes:
            return True
    # No :-(
    return False


def map_project_values(data):
    data = copy.deepcopy(data)

    # STAGE_DEVELOPMENT
    value_sd = jsonpointer.resolve_pointer(data, "/stage_development/value", None)
    if value_sd in TYPE_PROJECT_MAP_VALUES_STAGE_DEVELOPMENT.keys():
        jsonpointer.set_pointer(
            data,
            "/stage_development/value",
            TYPE_PROJECT_MAP_VALUES_STAGE_DEVELOPMENT[value_sd],
        )

    # PURPOSE_AND_CLASSIFICATIONS_POLICY_SECTOR
    value_pacps = jsonpointer.resolve_pointer(
        data, "/purpose_and_classifications/policy_sector/value", None
    )
    if (
        value_pacps
        in TYPE_PROJECT_MAP_VALUES_PURPOSE_AND_CLASSIFICATIONS_POLICY_SECTOR.keys()
    ):
        jsonpointer.set_pointer(
            data,
            "/purpose_and_classifications/policy_sector/value",
            TYPE_PROJECT_MAP_VALUES_PURPOSE_AND_CLASSIFICATIONS_POLICY_SECTOR[
                value_pacps
            ],
        )

    # Done
    return data
