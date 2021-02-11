import os

import spreadsheetforms
from django.conf import settings
from django.core.management.base import BaseCommand

from indigo.models import Fund, Organisation, Project
from indigo.spreadsheetforms import (
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
)


class Command(BaseCommand):
    help = "Dump all Private Data to Disk"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        # DIRS
        out_projects_dirname = os.path.join(
            settings.BASE_DIR, "dump_private_data", "projects"
        )
        out_funds_dirname = os.path.join(
            settings.BASE_DIR, "dump_private_data", "funds"
        )
        out_organisations_dirname = os.path.join(
            settings.BASE_DIR, "dump_private_data", "organisations"
        )
        os.makedirs(out_projects_dirname, exist_ok=True)
        os.makedirs(out_funds_dirname, exist_ok=True)
        os.makedirs(out_organisations_dirname, exist_ok=True)
        # FUNDS
        for fund in Fund.objects.all():

            guide_file = os.path.join(
                settings.BASE_DIR, "indigo", "spreadsheetform_guides", "fund_v001.xlsx",
            )

            out_file = os.path.join(out_funds_dirname, fund.public_id + ".xlsx")

            data = convert_fund_data_to_spreadsheetforms_data(fund, public_only=False)

            spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)
        # ORGANISATIONS
        for organisation in Organisation.objects.all():

            guide_file = os.path.join(
                settings.BASE_DIR,
                "indigo",
                "spreadsheetform_guides",
                "organisation_v001.xlsx",
            )

            out_file = os.path.join(
                out_organisations_dirname, organisation.public_id + ".xlsx"
            )

            data = convert_organisation_data_to_spreadsheetforms_data(
                organisation, public_only=False
            )

            spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

        # PROJECTS
        for project in Project.objects.all():

            guide_file = os.path.join(
                settings.BASE_DIR,
                "indigo",
                "spreadsheetform_guides",
                "project_v002.xlsx",
            )

            out_file = os.path.join(out_projects_dirname, project.public_id + ".xlsx")

            data = convert_project_data_to_spreadsheetforms_data(
                project, public_only=False
            )

            spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)
