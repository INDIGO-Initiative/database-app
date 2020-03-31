from django import forms


class ProjectNewForm(forms.Form):
    id = forms.SlugField()
    title = forms.CharField()


class ProjectImportForm(forms.Form):
    file = forms.FileField()


class ProjectMakeDisputedForm(forms.Form):
    pass


class ProjectMakePrivateForm(forms.Form):
    pass
