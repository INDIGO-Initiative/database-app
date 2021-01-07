import jsonschema
from django.conf import settings


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

            else:
                pass
                # print("UNCAUGHT JSON SCHEMA ERROR")
                # print(error.message)
                # print(error.validator)
                # TODO should log and work on more errors here

        self.errors = errors

    def get_errors(self):
        return self.errors


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


class ValueNotSetDataError(_DataError):
    def __init__(self, error):
        self._path = "/".join([str(i) for i in error.path])

    def get_type(self):
        return "value_not_set"

    def get_path(self):
        return self._path


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
