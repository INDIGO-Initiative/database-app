import json
import os
from functools import lru_cache

import jsonpointer
import jsonschema
from django.conf import settings

from indigo import (
    TYPE_PROJECT_SOURCE_LIST,
    TYPE_PROJECT_SOURCES_REFERENCES,
    TYPE_PROJECT_SOURCES_REFERENCES_LIST,
)


@lru_cache
def get_project_priority_information():
    fn = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "jsonschema",
        "cached_information",
        "project.json.priorities.json",
    )
    with open(fn) as fp:
        return json.load(fp)


def get_priority_for_key(key):
    if not key.startswith("/"):
        key = "/" + key
    for info in get_project_priority_information():
        if key.startswith(info["key"]):
            return info["priority"]
    return 3


class DataQualityReportForProject:
    def __init__(self, project_data):
        self.project_data = project_data
        self.errors = []
        self._process()

    def _process(self):

        # Get errors; convert to our objects
        errors = []
        v = jsonschema.Draft7Validator(
            settings.JSONDATAFERRET_TYPE_INFORMATION["project"]["json_schema"]
        )
        for error in v.iter_errors(self.project_data):
            if (
                error.message.find("' is not one of [") != -1
                and error.validator == "enum"
            ):
                errors.append(ValueNotInEnumListDataError(error))

            elif (
                error.message == "None is not of type 'string'"
                and error.validator == "type"
                and error.validator_value == "string"
            ):
                errors.append(ValueNotSetDataError(error))

            elif (
                error.message.find("' does not match '") != -1
                and error.validator == "pattern"
            ):
                errors.append(ValueNotCorrectPatternError(error))

            elif (
                error.message.endswith(" is not of type 'number'")
                and error.validator == "type"
                and error.instance
            ):
                errors.append(ValueNotANumberDataError(error))

            elif error.validator == "minItems":
                errors.append(ArrayHasTooFewItemsError(error))

            else:
                pass
                # print("UNCAUGHT JSON SCHEMA ERROR")
                # print(error.message)
                # print(error.validator)
                # TODO should log and work on more errors here

        (
            source_ids_used_that_are_not_in_sources_table,
            source_table_entries_that_are_not_used,
        ) = _check_project_data_for_source_errors(self.project_data)

        for source_data in source_ids_used_that_are_not_in_sources_table:
            errors.append(
                SourceIdUsedThatIsNotInSourcesTable(source_data.get("source_id"))
            )
        for source_data in source_table_entries_that_are_not_used:
            errors.append(SourceIdNotUsed(source_data.get("source_id")))

        self.errors = errors

    def get_errors(self):
        return self.errors

    def get_errors_in_priority_levels(self):
        out = {0: [], 1: [], 2: [], 3: []}
        for error in self.errors:
            out[error.get_priority()].append(error)
        return out

    def get_errors_for_priority_level(self, level):
        return [e for e in self.errors if e.get_priority() == 0]

    def get_count_errors_in_priority_levels(self):
        out = {0: 0, 1: 0, 2: 0, 3: 0}
        for error in self.errors:
            out[error.get_priority()] += 1
        return out


def _check_project_data_for_source_errors(input_json):
    source_table_entries_that_are_not_used = []
    source_ids_referenced_that_are_not_in_sources_table = []
    source_ids_referenced = []
    source_ids_found = []

    # ----------------- Find all Source ID's referenced in data
    for key in TYPE_PROJECT_SOURCES_REFERENCES:
        field_value = jsonpointer.resolve_pointer(input_json, key, default="")
        if isinstance(field_value, str):
            for source_id in [s.strip() for s in field_value.strip().split(",")]:
                if source_id:
                    source_ids_referenced.append({"source_id": source_id})

    for config in TYPE_PROJECT_SOURCES_REFERENCES_LIST:
        data_list = jsonpointer.resolve_pointer(
            input_json, config["list_key"], default=None
        )
        if isinstance(data_list, list) and data_list:
            for item in data_list:
                field_value = jsonpointer.resolve_pointer(
                    item, config["item_source_ids_key"], default=""
                )
                if field_value:
                    for source_id in [
                        s.strip() for s in field_value.strip().split(",")
                    ]:
                        if source_id:
                            source_ids_referenced.append({"source_id": source_id})

    # -------------------- Now look through source table
    source_list = jsonpointer.resolve_pointer(
        input_json, TYPE_PROJECT_SOURCE_LIST["list_key"], default=None
    )
    if isinstance(source_list, list) and source_list:
        # Look through source table looking for problems
        for source_item in source_list:
            source_id = jsonpointer.resolve_pointer(
                source_item, TYPE_PROJECT_SOURCE_LIST["item_id_key"], default=""
            )
            if source_id:
                source_id = str(source_id).strip()
                source_ids_found.append(source_id)
                # Is this source ID used? Add to list if not
                if (
                    len(
                        [
                            s
                            for s in source_ids_referenced
                            if s["source_id"] == source_id
                        ]
                    )
                    == 0
                ):
                    source_table_entries_that_are_not_used.append(
                        {"source_id": source_id}
                    )

    # ----------------- Finally find any sources referenced that aren't in source table
    for source_id_reference in source_ids_referenced:
        if (
            len([s for s in source_ids_found if s == source_id_reference["source_id"]])
            == 0
        ):
            source_ids_referenced_that_are_not_in_sources_table.append(
                source_id_reference
            )

    # ----------------- Done
    return (
        source_ids_referenced_that_are_not_in_sources_table,
        source_table_entries_that_are_not_used,
    )


class _DataError:
    pass


class ValueNotInEnumListDataError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])
        self._value = error.instance
        self._value_options = error.validator_value

    def get_type(self):
        return "value_not_in_enum_list"

    def get_value(self):
        return self._value

    def get_value_options(self):
        return self._value_options

    def get_path(self):
        return self._path

    def get_priority(self):
        return 0


class ValueNotSetDataError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])
        self._priority = get_priority_for_key(self._path)

    def get_type(self):
        return "value_not_set"

    def get_path(self):
        return self._path

    def get_priority(self):
        return self._priority


class ValueNotCorrectPatternError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])
        self._value = error.instance
        self._pattern_hint = error.schema.get("patternHint")

    def get_type(self):
        return "value_not_correct_pattern"

    def get_path(self):
        return self._path

    def get_value(self):
        return self._value

    def get_pattern_hint(self):
        return self._pattern_hint

    def get_priority(self):
        return 0


class ValueNotANumberDataError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])
        self._value = error.instance

    def get_type(self):
        return "value_not_a_number"

    def get_path(self):
        return self._path

    def get_value(self):
        return self._value

    def get_priority(self):
        return 0


class ArrayHasTooFewItemsError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])
        self._value = error.instance

    def get_type(self):
        return "array_has_too_few_items"

    def get_path(self):
        return self._path

    def get_value(self):
        return self._value

    def get_priority(self):
        return 0


class SourceIdUsedThatIsNotInSourcesTable(_DataError):
    def __init__(self, source_id):
        self.source_id = source_id

    def get_type(self):
        return "source_id_used_that_is_not_in_sources_table"

    def get_path(self):
        return None

    def get_value(self):
        return self.source_id

    def get_priority(self):
        return 0


class SourceIdNotUsed(_DataError):
    def __init__(self, source_id):
        self.source_id = source_id

    def get_type(self):
        return "source_id_not_used"

    def get_path(self):
        return None

    def get_value(self):
        return self.source_id

    def get_priority(self):
        return 0
