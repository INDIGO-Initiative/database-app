from djangoproject.util import JsonSchemaProcessor
import os
import pprint


input_filename = os.path.join("indigo", "jsonschema", "project.json")

p = JsonSchemaProcessor(input_filename=input_filename)
fields = p.get_fields()

pp = pprint.PrettyPrinter(indent=4)

pp.pprint(fields)
