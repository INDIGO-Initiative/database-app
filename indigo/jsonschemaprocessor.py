import jsonpointer
from compiletojsonschema.compiletojsonschema import CompileToJsonSchema


class JsonSchemaProcessor:
    def __init__(self, input_filename):
        compile = CompileToJsonSchema(input_filename)
        self.json_schema_compiled = compile.get()

    def get_fields(self):
        return self._get_fields_worker(
            json_schema=self.json_schema_compiled, start_pointer="", title=""
        )

    def _get_fields_worker(self, json_schema, start_pointer, title):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(json_schema, start_pointer)
        if our_json_schema.get("type") == "object":
            for key in our_json_schema.get("properties").keys():
                out.extend(
                    self._get_fields_worker(
                        json_schema=json_schema,
                        start_pointer=start_pointer + "/properties/" + key,
                        title=self._join_title(title, our_json_schema.get("title", "")),
                    )
                )
        elif our_json_schema.get("type") in ["string", "number"]:
            out.append(
                {
                    "key": start_pointer.replace("/properties/", "/"),
                    "title": self._join_title(title, our_json_schema.get("title", "")),
                }
            )
        elif our_json_schema.get("type") == "array":
            new_json_schema = jsonpointer.resolve_pointer(
                json_schema, start_pointer + "/items"
            )
            out.append(
                {
                    "type": "list",
                    "key": start_pointer.replace("/properties/", "/"),
                    "title": self._join_title(title, our_json_schema.get("title", "")),
                    "fields": self._get_fields_worker(
                        json_schema=new_json_schema, start_pointer="", title="",
                    ),
                }
            )

        return out

    def _join_title(self, bit1, bit2):
        if bit1 and bit2:
            return bit1.strip() + " - " + bit2.strip()
        elif bit1:
            return bit1.strip()
        elif bit2:
            return bit2.strip()
        else:
            return ""

    def get_filter_keys(self):
        return self._get_filter_keys_worker(start_pointer="")

    def _get_filter_keys_worker(
        self, start_pointer,
    ):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(
            self.json_schema_compiled, start_pointer
        )
        if our_json_schema.get("type") == "object":
            for key in our_json_schema.get("properties").keys():
                if key != "status":
                    out.extend(
                        self._get_filter_keys_worker(
                            start_pointer=start_pointer + "/properties/" + key,
                        )
                    )
                elif start_pointer != "":
                    out.append(start_pointer.replace("/properties/", "/"))
        return out
