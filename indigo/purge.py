from jsondataferret.pythonapi.purge import purge_record

from indigo.models import (
    ProjectImport,
    ProjectIncludesFund,
    ProjectIncludesOrganisation,
)


def purge_project(project):

    for data in ProjectImport.objects.filter(project=project):
        data.delete()

    for data in ProjectIncludesOrganisation.objects.filter(project=project):
        data.delete()

    for data in ProjectIncludesFund.objects.filter(project=project):
        data.delete()

    project.delete()

    purge_record(project.record)


def purge_organisation(organisation):

    for data in ProjectIncludesOrganisation.objects.filter(organisation=organisation):
        data.delete()

    organisation.delete()

    purge_record(organisation.record)
