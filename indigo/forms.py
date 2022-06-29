from django import forms

COMMENT_LABEL = "Comment for history"


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
