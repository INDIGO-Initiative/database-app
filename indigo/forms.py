import json
import os

import jsonschema
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.urls import reverse

COMMENT_LABEL = "Comment for history"


class StyledAuthenticationForm(AuthenticationForm):
    """The login form, with Bootstrap-styled fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update({"class": "form-control"})


class RJSFWidget(forms.Widget):
    """Edits JSON with a React JSON Schema Form (RJSF), loaded from the bundle in indigo/static/rjsf/.

    The source is in frontend/. The data is kept in a hidden input, as a JSON string, and the bundle fills in the rest."""

    template_name = "indigo/rjsf_widget.html"

    class Media:
        css = {"all": ("rjsf/rjsf-form.css",)}
        js = ("rjsf/rjsf-form.js",)

    def __init__(self, schema, type_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema
        self.type_id = type_id

    def format_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return super().format_value(value)

    def get_context(self, name, value, attrs):
        # RJSFBoundField gives us the errors from the last check of the schema, so they can be shown against the fields
        attrs = dict(attrs or {})
        errors = attrs.pop("rjsf_errors", [])
        context = super().get_context(name, value, attrs)
        context["widget"]["schema"] = self.schema
        context["widget"]["schema_id"] = f"{context['widget']['attrs']['id']}_schema"
        context["widget"]["errors"] = errors
        context["widget"]["errors_id"] = f"{context['widget']['attrs']['id']}_errors"
        context["widget"]["type_id"] = self.type_id
        context["widget"]["organisation_search_url"] = reverse(
            "indigo_admin_organisation_search_json"
        )
        return context


class RJSFSchemaField(forms.CharField):
    """JSON data, edited with RJSF and checked against a JSON Schema on the server."""

    def __init__(self, schema, type_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema
        self.widget = RJSFWidget(schema=schema, type_id=type_id)

    def prepare_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError("Invalid JSON")
        return value

    def get_bound_field(self, form, field_name):
        return RJSFBoundField(form, self, field_name)

    def clean(self, value):
        value = super().clean(value)
        errors = schema_errors(self.schema, value)
        if errors:
            raise ValidationError(
                [SchemaValidationError(message, path) for path, message in errors]
            )
        return value


class SchemaValidationError(ValidationError):
    """A problem with one part of the data. path is a JSON pointer to that part, eg /outcome_funds/0/id"""

    def __init__(self, message, path):
        super().__init__(
            f"{path}: {message}" if path else message,
            code="schema",
        )
        self.path = path
        self.plain_message = message


class RJSFBoundField(forms.BoundField):
    def as_widget(self, widget=None, attrs=None, only_initial=False):
        attrs = dict(attrs or {})
        attrs["rjsf_errors"] = [
            {"path": e.path, "message": e.plain_message}
            for e in self.form.errors.as_data().get(self.name, [])
            if isinstance(e, SchemaValidationError)
        ]
        return super().as_widget(widget, attrs, only_initial)


MAX_SCHEMA_ERRORS = 50


def _pointer(parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def schema_errors(schema, value):
    """Problems with value found by checking it against the JSON Schema, as a list of (JSON pointer, message)."""
    found = []
    for error in sorted(
        jsonschema.Draft7Validator(schema).iter_errors(value),
        key=lambda e: [str(p) for p in e.absolute_path],
    ):
        path = list(error.absolute_path)
        if error.validator == "required":
            # Show these against the missing field, not the group it is missing from
            for key in error.validator_value:
                if key not in error.instance:
                    found.append((_pointer(path + [key]), "This field is required"))
        else:
            found.append((_pointer(path), error.message))
    return found[:MAX_SCHEMA_ERRORS]


BASE_PATH = os.path.join(os.path.dirname(__file__), "jsonschema", "cached_information")


def load_schema_data(filename):
    """
    Load a models data field json schema from a file
    """
    data = None

    try:
        with open(filename, "r") as f:
            data = json.load(f)

    except Exception as e:
        print(f"Problem loading JSON schema: {e}")

    return data


JOINING_UP_INITIATIVE_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "joining_up_initiative.json.compiled_jsonschema.json")
)
PROJECT_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "project.json.compiled_jsonschema.json")
)
FUND_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "fund.json.compiled_jsonschema.json")
)
PIPELINE_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "pipeline.json.compiled_jsonschema.json")
)
ASSESSMENT_RESOURCE_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "assessment_resource.json.compiled_jsonschema.json")
)
ORGANISATION_SCHEMA = load_schema_data(
    os.path.join(BASE_PATH, "organisation.json.compiled_jsonschema.json")
)


class NewRecordForm(forms.Form):
    """The first step of adding a record: just a name. The rest of the details are filled in on the edit form next."""

    name = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True})
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label=COMMENT_LABEL,
        initial="Created",
        help_text="Why this is being added. It is kept in the history of the record.",
    )


class ProjectNewForm(NewRecordForm):
    pass


class ModelImportStage1Of2Form(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={"class": "custom-file-input"}))


class ModelImportStage2Of2Form(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationNewForm(NewRecordForm):
    pass


class OrganisationImportForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={"class": "custom-file-input"}))
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationEditForm(forms.Form):
    data = RJSFSchemaField(label="", schema=ORGANISATION_SCHEMA, type_id="organisation")
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class ProjectEditForm(forms.Form):
    data = RJSFSchemaField(label="", schema=PROJECT_SCHEMA, type_id="project")
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class FundEditForm(forms.Form):
    data = RJSFSchemaField(label="", schema=FUND_SCHEMA, type_id="fund")
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class PipelineEditForm(forms.Form):
    data = RJSFSchemaField(label="", schema=PIPELINE_SCHEMA, type_id="pipeline")
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class AssessmentResourceEditForm(forms.Form):
    data = RJSFSchemaField(
        label="", schema=ASSESSMENT_RESOURCE_SCHEMA, type_id="assessment_resource"
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class FundNewForm(NewRecordForm):
    pass


class AssessmentResourceNewForm(NewRecordForm):
    pass


class PipelineNewForm(NewRecordForm):
    pass


class JoiningUpInitiativeNewForm(forms.Form):
    data = RJSFSchemaField(
        label="",
        schema=JOINING_UP_INITIATIVE_SCHEMA,
        type_id="joining_up_initiative",
    )
    comment = forms.CharField(widget=forms.HiddenInput, initial="Created")


class JoiningUpInitiativeEditForm(forms.Form):
    data = RJSFSchemaField(
        label="",
        schema=JOINING_UP_INITIATIVE_SCHEMA,
        type_id="joining_up_initiative",
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class ModelImportForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={"class": "custom-file-input"}))
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class RecordChangeStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            ("PUBLIC", "PUBLIC"),
            ("PRIVATE", "PRIVATE"),
            ("DISPUTED", "DISPUTED"),
        ],
        widget=forms.Select(attrs={"class": "custom-select"}),
    )
    when = forms.ChoiceField(
        choices=[
            ("moderate", "Submit for moderation"),
            ("immediate", "Make change IMMEDIATELY"),
        ],
        widget=forms.Select(attrs={"class": "custom-select"}),
    )
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)
