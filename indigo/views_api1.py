from abc import ABC

from django.conf import settings
from django.http import Http404, JsonResponse
from django.views import View

from .models import (
    AssessmentResource,
    Fund,
    JoiningUpInitiative,
    Organisation,
    Pipeline,
    Project,
)

########################### Public - Project - API


def api1_projects_list(request):
    projects = Project.objects.filter()
    data = {
        "projects": [
            {"id": p.public_id, "public": (p.exists and p.status_public)}
            for p in projects
        ]
    }
    return JsonResponse(data)


def api1_project_index(request, public_id):
    try:
        project = Project.objects.get(public_id=public_id)
    except Project.DoesNotExist:
        raise Http404("Project does not exist")
    if not project.status_public or not project.exists:
        raise Http404("Project does not exist")

    data = {
        "project": {
            "id": project.public_id,
            "data": project.data_public,
        }
    }
    if (
        settings.API_SANDBOX_DATA_PASSWORD
        and request.GET.get("sandbox_data_password", "")
        == settings.API_SANDBOX_DATA_PASSWORD
    ):
        data["project"]["sandboxes"] = project.data_sandboxes
    return JsonResponse(data)


########################### Public - Organisation - API


def api1_organisations_list(request):
    organisations = Organisation.objects.filter()
    data = {
        "organisations": [
            {"id": p.public_id, "public": (p.exists and p.status_public)}
            for p in organisations
        ]
    }
    return JsonResponse(data)


def api1_organisation_index(request, public_id):
    try:
        organisation = Organisation.objects.get(public_id=public_id)
    except Organisation.DoesNotExist:
        raise Http404("Organisation does not exist")
    if not organisation.status_public or not organisation.exists:
        raise Http404("Organisation does not exist")

    data = {
        "organisation": {
            "id": organisation.public_id,
            "data": organisation.data_public,
        }
    }
    return JsonResponse(data)


########################### Public - Fund & Assesment Resource - API


class API1ModelList(View, ABC):
    def get(self, request):
        datas = self.__class__._model.objects.filter().order_by("public_id")
        output = {
            self.__class__._model.type_id
            + "s": [
                {"id": d.public_id, "public": (d.exists and d.status_public)}
                for d in datas
            ]
        }
        return JsonResponse(output)


class API1FundList(API1ModelList):
    _model = Fund


class API1AssessmentResourceList(API1ModelList):
    _model = AssessmentResource


class API1PipelineList(API1ModelList):
    _model = Pipeline


class API1JoiningUpInitiativeList(API1ModelList):
    _model = JoiningUpInitiative


class API1ModelIndex(View, ABC):
    def get(self, request, public_id):
        try:
            data = self.__class__._model.objects.get(
                exists=True, status_public=True, public_id=public_id
            )
        except self._model.DoesNotExist:
            raise Http404("Data does not exist")
        if not data.status_public or not data.exists:
            raise Http404("Data does not exist")
        data = {
            self.__class__._model.type_id: {
                "id": data.public_id,
                "data": data.data_public,
            }
        }
        return JsonResponse(data)


class API1FundIndex(API1ModelIndex):
    _model = Fund


class API1AssessmentResourceIndex(API1ModelIndex):
    _model = AssessmentResource


class API1PipelineIndex(API1ModelIndex):
    _model = Pipeline


class API1JoiningUpInitiativeIndex(API1ModelIndex):
    _model = JoiningUpInitiative
