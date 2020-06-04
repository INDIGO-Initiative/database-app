from django import forms


class ProjectNewForm(forms.Form):
    id = forms.SlugField()
    title = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea)


class ProjectImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea)


class ProjectMakeDisputedForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea)


class ProjectMakePrivateForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea)


class OrganisationNewForm(forms.Form):
    id = forms.SlugField()
    title = forms.CharField()
    comment = forms.CharField(widget=forms.Textarea)


class OrganisationImportForm(forms.Form):
    file = forms.FileField()
    comment = forms.CharField(widget=forms.Textarea)
