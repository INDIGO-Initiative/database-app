import glob
import json
import os

from django.conf import settings
from spreadsheetforms.api import get_guide_spec

from indigo.jsonschemaprocessor import JsonSchemaProcessor


def cache_spreadsheet_guide_info():
    guide_file_glob = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "*.xlsx",
    )
    for filename in glob.glob(guide_file_glob):
        filename_bits = filename.split("/")
        out_filename = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "spreadsheetform_guides",
            "cached_information",
            filename_bits[-1] + ".guidespec.json",
        )
        data = get_guide_spec(filename)
        with open(out_filename, "w") as fp:
            json.dump(data, fp, sort_keys=True, indent=4)


def cache_json_schema_info():
    guide_file_glob = os.path.join(settings.BASE_DIR, "indigo", "jsonschema", "*.json",)
    for filename in glob.glob(guide_file_glob):
        filename_bits = filename.split("/")
        data = JsonSchemaProcessor(filename)
        # Fields
        out_filename_fields = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".fields.json",
        )
        with open(out_filename_fields, "w") as fp:
            json.dump(data.get_fields(), fp, sort_keys=True, indent=4)
        # Filter keys
        out_filename_filter_keys = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".filter_keys.json",
        )
        with open(out_filename_filter_keys, "w") as fp:
            json.dump(data.get_filter_keys(), fp, sort_keys=True, indent=4)
        # Priorities
        out_filename_filter_keys = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".priorities.json",
        )
        with open(out_filename_filter_keys, "w") as fp:
            json.dump(data.get_priorities(), fp, sort_keys=True, indent=4)
