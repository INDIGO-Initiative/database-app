import os
import tempfile
from zipfile import ZipFile

import spreadsheetforms.api
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import indigo.utils
from indigo.models import Fund, Organisation, Project


def update_public_files_for_project(project):
    if project.exists and project.status_public:
        _write_public_files_for_project(project)
    else:
        _remove_public_files_for_project(project)


def _remove_public_files_for_project(project):
    default_storage_name_xlsx = "public/project/" + project.public_id + ".xlsx"
    if default_storage.exists(default_storage_name_xlsx):
        default_storage.delete(default_storage_name_xlsx)


def _write_public_files_for_project(project):
    default_storage_name_xlsx = "public/project/" + project.public_id + ".xlsx"

    # --- Get Data
    data = indigo.processdata.add_other_records_to_project(
        project.public_id, project.data_public, public_only=True
    )

    # --- XLSX File
    guide_file = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "spreadsheetform_guides",
        "project_public_v009.xlsx",
    )

    # Create in Temp
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    out_file = file.name
    file.close()
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    # Move to Django Storage
    default_storage.delete(default_storage_name_xlsx)
    with open(out_file, "rb") as fp:
        default_storage.save(default_storage_name_xlsx, ContentFile(fp.read()))

    # Delete Temp file
    os.remove(out_file)


def update_public_files_for_organisation(organisation):
    if organisation.exists and organisation.status_public:
        _write_public_files_for_organisation(organisation)
    else:
        _remove_public_files_for_organisation(organisation)


def _remove_public_files_for_organisation(organisation):
    default_storage_name_xlsx = (
        "public/organisation/" + organisation.public_id + ".xlsx"
    )
    if default_storage.exists(default_storage_name_xlsx):
        default_storage.delete(default_storage_name_xlsx)


def _write_public_files_for_organisation(organisation):
    default_storage_name_xlsx = (
        "public/organisation/" + organisation.public_id + ".xlsx"
    )

    # --- Get Data
    data = indigo.processdata.add_other_records_to_organisation(
        organisation.public_id, organisation.data_public, public_only=True
    )

    # --- XLSX File
    guide_file = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "spreadsheetform_guides",
        "organisation_public_v002.xlsx",
    )

    # Create in Temp
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    out_file = file.name
    file.close()
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    # Move to Django Storage
    default_storage.delete(default_storage_name_xlsx)
    with open(out_file, "rb") as fp:
        default_storage.save(default_storage_name_xlsx, ContentFile(fp.read()))

    # Delete Temp file
    os.remove(out_file)


def update_public_files_for_fund(fund):
    if fund.exists and fund.status_public:
        _write_public_files_for_fund(fund)
    else:
        _remove_public_files_for_fund(fund)


def _remove_public_files_for_fund(fund):
    default_storage_name_xlsx = "public/fund/" + fund.public_id + ".xlsx"
    if default_storage.exists(default_storage_name_xlsx):
        default_storage.delete(default_storage_name_xlsx)


def _write_public_files_for_fund(fund):
    default_storage_name_xlsx = "public/fund/" + fund.public_id + ".xlsx"

    # --- Get Data
    data = indigo.processdata.add_other_records_to_fund(
        fund.public_id, fund.data_public, public_only=True
    )

    # --- XLSX File
    guide_file = os.path.join(
        settings.BASE_DIR, "indigo", "spreadsheetform_guides", "fund_public_v001.xlsx",
    )

    # Create in Temp
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    out_file = file.name
    file.close()
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    # Move to Django Storage
    default_storage.delete(default_storage_name_xlsx)
    with open(out_file, "rb") as fp:
        default_storage.save(default_storage_name_xlsx, ContentFile(fp.read()))

    # Delete Temp file
    os.remove(out_file)


def update_public_archive_files():

    # --- XLSX Files

    # Create Temp Files
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    out_file = file.name
    file.close()

    # Contents
    with ZipFile(out_file, "w") as zipfile:

        for organisation in Organisation.objects.filter(
            exists=True, status_public=True
        ):
            _put_file_in_zip_file(
                zipfile,
                "public/organisation/" + organisation.public_id + ".xlsx",
                "organisation/" + organisation.public_id + ".xlsx",
            )

        for fund in Fund.objects.filter(exists=True, status_public=True):
            _put_file_in_zip_file(
                zipfile,
                "public/fund/" + fund.public_id + ".xlsx",
                "fund/" + fund.public_id + ".xlsx",
            )

        for project in Project.objects.filter(exists=True, status_public=True):
            _put_file_in_zip_file(
                zipfile,
                "public/project/" + project.public_id + ".xlsx",
                "project/" + project.public_id + ".xlsx",
            )

    # Move to Django Storage
    default_storage.delete("public/all_data_as_spreadsheets.zip")
    with open(out_file, "rb") as fp:
        default_storage.save(
            "public/all_data_as_spreadsheets.zip", ContentFile(fp.read())
        )

    # Delete Temp file
    os.remove(out_file)


def _put_file_in_zip_file(zipfile, file_name_in_storage, file_name_in_zip):
    if default_storage.exists(file_name_in_storage):
        with default_storage.open(file_name_in_storage, "rb") as fp:
            zipfile.writestr(file_name_in_zip, fp.read())
