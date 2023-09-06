import json
import os

from django import forms
from django_jsonforms.forms import JSONSchemaField

COMMENT_LABEL = "Comment for history"

JSONFORMS_OPTIONS = {
    "theme": "bootstrap4",
    "no_additional_properties": True,
    "show_errors": "always",
    "compact": False,
    "iconlib": "fontawesome5",
    "disable_edit_json": True,
    "disable_collapse": True,
    "disable_edit_json": True,
    "disable_properties": True,
}

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


class ProjectNewForm(forms.Form):
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class ModelImportStage1Of2Form(forms.Form):
    file = forms.FileField()


class ModelImportStage2Of2Form(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationNewForm(forms.Form):
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class FundNewForm(forms.Form):
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class AssessmentResourceNewForm(forms.Form):
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class PipelineNewForm(forms.Form):
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class JoiningUpInitiativeNewForm(forms.Form):
    data = JSONSchemaField(
        label="",
        schema=JOINING_UP_INITIATIVE_SCHEMA,
        options=JSONFORMS_OPTIONS,
        ajax=False,
    )
    comment = forms.CharField(widget=forms.HiddenInput, initial="Created")


class JoiningUpInitiativeEditForm(forms.Form):
    data = JSONSchemaField(
        label="",
        schema=JOINING_UP_INITIATIVE_SCHEMA,
        options=JSONFORMS_OPTIONS,
        ajax=False,
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control"}), label=COMMENT_LABEL
    )


class ModelImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class RecordChangeStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("PUBLIC", "PUBLIC"), ("PRIVATE", "PRIVATE"), ("DISPUTED", "DISPUTED")]
    )
    when = forms.ChoiceField(
        choices=[
            ("moderate", "Submit for moderation"),
            ("immediate", "Make change IMMEDIATELY"),
        ]
    )
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)
