from django import forms

COMMENT_LABEL = "Comment for history"


class ProjectNewForm(forms.Form):
    id = forms.SlugField()
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
    id = forms.SlugField()
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class OrganisationImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class FundNewForm(forms.Form):
    id = forms.SlugField()
    name = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)


class FundImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea, label=COMMENT_LABEL)
