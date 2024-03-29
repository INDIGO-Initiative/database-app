import jsonpointer
from compiletojsonschema.compiletojsonschema import CompileToJsonSchema


class JsonSchemaProcessor:
    def __init__(self, input_filename, codelist_base_directory=None):
        compile = CompileToJsonSchema(
            input_filename, codelist_base_directory=codelist_base_directory
        )
        self._json_schema_compiled = compile.get()

    def get_json_schema_compiled(self):
        return self._json_schema_compiled

    def get_fields(self):
        return self._get_fields_worker(
            json_schema=self._json_schema_compiled, start_pointer="", title=""
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
                    "type": our_json_schema.get("type"),
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
                        json_schema=new_json_schema,
                        start_pointer="",
                        title="",
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
        self,
        start_pointer,
    ):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(
            self._json_schema_compiled, start_pointer
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

    def get_priorities(self):
        return self._get_priorities_worker(
            json_schema=self._json_schema_compiled, start_pointer=""
        )

    def _get_priorities_worker(self, json_schema, start_pointer):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(json_schema, start_pointer)
        if our_json_schema.get("type") == "object":
            for key in our_json_schema.get("properties").keys():
                out.extend(
                    self._get_priorities_worker(
                        json_schema=json_schema,
                        start_pointer=start_pointer + "/properties/" + key,
                    )
                )

        if "priority" in our_json_schema:
            out.append(
                {
                    "key": start_pointer.replace("/properties/", "/"),
                    "priority": our_json_schema.get("priority"),
                }
            )

        return out

    def get_references_to_model(self):
        return self._get_references_to_model_worker(
            json_schema=self._json_schema_compiled, start_pointer=""
        )

    def _get_references_to_model_worker(self, json_schema, start_pointer):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(json_schema, start_pointer)
        if our_json_schema.get("type") == "object":
            for key in our_json_schema.get("properties").keys():
                out.extend(
                    self._get_references_to_model_worker(
                        json_schema=json_schema,
                        start_pointer=start_pointer + "/properties/" + key,
                    )
                )
        if our_json_schema.get("type") == "array":
            out.extend(
                self._get_references_to_model_worker(
                    json_schema=json_schema,
                    start_pointer=start_pointer + "/items",
                )
            )

        if our_json_schema.get("references-model"):
            key_bits = start_pointer.replace("/properties/", "/").split("/items", 2)
            out.append(
                {
                    "list_key": key_bits[0],
                    "item_key": key_bits[1],
                    "model": our_json_schema.get("references-model"),
                    "multiple-seperator": our_json_schema.get(
                        "references-models-seperator"
                    ),
                }
            )

        return out

    def get_references_to_data(self):
        return self._get_references_to_data_worker(
            json_schema=self._json_schema_compiled, start_pointer=""
        )

    def _get_references_to_data_worker(self, json_schema, start_pointer):
        out = []
        our_json_schema = jsonpointer.resolve_pointer(json_schema, start_pointer)
        if our_json_schema.get("type") == "object":
            for key in our_json_schema.get("properties").keys():
                out.extend(
                    self._get_references_to_data_worker(
                        json_schema=json_schema,
                        start_pointer=start_pointer + "/properties/" + key,
                    )
                )
        if our_json_schema.get("type") == "array":
            out.extend(
                self._get_references_to_data_worker(
                    json_schema=json_schema,
                    start_pointer=start_pointer + "/items",
                )
            )

        if our_json_schema.get("references-data-key"):
            if "/items" in start_pointer:
                key_bits = start_pointer.replace("/properties/", "/").split("/items", 2)
                out.append(
                    {
                        "list_key": key_bits[0],
                        "item_key": key_bits[1],
                        "data_key": our_json_schema.get("references-data-key"),
                        "data_list": our_json_schema.get("references-data-list"),
                        "multiple_seperator": our_json_schema.get(
                            "references-datas-seperator"
                        ),
                    }
                )
            else:
                out.append(
                    {
                        "item_key": start_pointer.replace("/properties/", "/"),
                        "data_key": our_json_schema.get("references-data-key"),
                        "data_list": our_json_schema.get("references-data-list"),
                        "multiple_seperator": our_json_schema.get(
                            "references-datas-seperator"
                        ),
                    }
                )

        return out
