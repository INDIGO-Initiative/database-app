import json
import os
from functools import lru_cache

import jsonschema
from django.conf import settings


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

        self.errors = errors

    def get_errors(self):
        return self.errors

    def get_errors_in_priority_levels(self):
        out = {0: [], 1: [], 2: [], 3: []}
        for error in self.errors:
            out[error.get_priority()].append(error)
        return out

    def get_count_errors_in_priority_levels(self):
        out = {0: 0, 1: 0, 2: 0, 3: 0}
        for error in self.errors:
            out[error.get_priority()] += 1
        return out


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
