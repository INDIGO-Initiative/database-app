import json

import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


class Command(BaseCommand):
    help = "Temp Data Migration - Import Documents"

    def add_arguments(self, parser):
        parser.add_argument("filename")

    def handle(self, *args, **options):
        with open(options["filename"]) as fp:
            all_datas = json.load(fp)

        writes = []

        for data in all_datas:
            documents = []
            for related_document in data.get("related_documents"):
                if _include_document(related_document.get("title")):
                    documents.append(
                        {
                            "title": {"value": related_document.get("title")},
                            "url": {
                                "value": "https://golab.bsg.ox.ac.uk"
                                + related_document.get("url")
                            },
                            "status": "PUBLIC",
                        }
                    )

            if documents:
                project = _get_project(data.get("project_title"))
                if project:
                    print("Project id: " + project.public_id)
                    print(
                        "Project title: "
                        + project.data_private.get("name").get("value")
                    )
                    for document in documents:
                        print("Adding Title: " + document.get("title").get("value"))
                        print("Adding URL: " + document.get("url").get("value"))
                    print()
                    writes.append(
                        NewEventData(
                            project.record.type,
                            project.record,
                            {"documents": documents},
                            mode=jsondataferret.EVENT_MODE_MERGE,
                            approved=True,
                        )
                    )
                else:
                    print("CAN NOT FIND PROJECT TITLE: " + data.get("project_title"))
                    for document in documents:
                        print("WOULD ADD TITLE: " + document.get("title").get("value"))
                        print("WOULD ADD URL: " + document.get("url").get("value"))
                    print()

        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment="Data Import - Documents",
            )


def _include_document(title):
    if title.startswith("Data Template"):
        return False
    if title.startswith("Data template"):
        return False
    if title.endswith("Data Template"):
        return False
    if title.endswith("Data Templates"):
        return False
    if title == "Data Dictionary":
        return False
    # Some special cases I've checked by hand
    if title == "Ventura County Project to Support Reentry - Fact Sheet":
        return False
    if title == "London Rough Sleepers St Mungo's":
        return False
    if title == "Rewriting Futures/St Basil's - Data Template (FCF)":
        return False
    if title == "Fusion - Data Template - Fair Chance Fund":
        return False
    if title == "Local Solutions - Data Template (FCF)":
        return False
    if title == "Home Group - Data Template (FCF)":
        return False
    # ok
    return True


def _get_project(title):
    try:
        return Project.objects.get(
            exists=True,
            status_public=True,
            data_private__name__value=_transform_project_title(title),
        )
    except Project.DoesNotExist:
        # First, some of our data has a space at the end - so try searching for that
        try:
            return Project.objects.get(
                exists=True,
                status_public=True,
                data_private__name__value=_transform_project_title(title) + " ",
            )
        except Project.DoesNotExist:
            # now we give up
            return None


def _transform_project_title(title):
    # Some special cases I've checked by hand
    if (
        title
        == "NYC Adolescent Behavioral Learning Experience Project for Incarcerated Youth"
    ):
        return "NYC Adolescent Behavioral Learning Experience (i.e. ABLE) Project for Incarcerated Youth"
    if title == "D.C. Water Environmental Bond":
        return "DC Water Environmental Bond"
    # ok
    return title
