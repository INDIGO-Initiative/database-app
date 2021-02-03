from django import forms

from indigo.utils import validate_fund_id, validate_organisation_id, validate_project_id

COMMENT_LABEL = "Comment for history"


class ProjectNewForm(forms.Form):
    id = forms.SlugField(validators=[validate_project_id], initial="INDIGO-POJ-0000")
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class ProjectImportForm(forms.Form):
    file = forms.FileField()


class ProjectImportStage2Form(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class ProjectMakeDisputedForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class ProjectMakePrivateForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationNewForm(forms.Form):
    id = forms.SlugField(
        validators=[validate_organisation_id], initial="INDIGO-ORG-0000"
    )
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class FundNewForm(forms.Form):
    id = forms.SlugField(validators=[validate_fund_id], initial="INDIGO-FUND-0000")
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class FundImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class RecordChangeStatusForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("PUBLIC", "PUBLIC"), ("PRIVATE", "PRIVATE"), ("DISPUTED", "DISPUTED")]
    )
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)
