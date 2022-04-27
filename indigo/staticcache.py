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
    filenames = glob.glob(
        os.path.join(settings.BASE_DIR, "data-standard", "schema", "*.json",)
    ) + glob.glob(
        os.path.join(
            settings.BASE_DIR, "data-standard-impact-wayfinder", "schema", "*.json",
        )
    )
    for filename in filenames:
        filename_bits = filename.split("/")
        data = JsonSchemaProcessor(
            filename,
            codelist_base_directory=os.path.join(
                settings.BASE_DIR, "data-standard", "schema", "codelists",
            ),
        )
        # Compiled JSONSchema
        out_filename_compiled_jsonschema = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".compiled_jsonschema.json",
        )
        with open(out_filename_compiled_jsonschema, "w") as fp:
            json.dump(data.get_json_schema_compiled(), fp, sort_keys=True, indent=4)
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
        # References Models
        out_filename_references_models = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".references_models.json",
        )
        with open(out_filename_references_models, "w") as fp:
            json.dump(data.get_references_to_model(), fp, sort_keys=True, indent=4)
        # References Datas
        out_filename_references_datas = os.path.join(
            settings.BASE_DIR,
            "indigo",
            "jsonschema",
            "cached_information",
            filename_bits[-1] + ".references_datas.json",
        )
        with open(out_filename_references_datas, "w") as fp:
            json.dump(data.get_references_to_data(), fp, sort_keys=True, indent=4)
