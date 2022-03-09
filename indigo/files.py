import csv
import io
import os
import tempfile
from zipfile import ZipFile

import jsonpointer
import spreadsheetforms.api
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from indigo.dataqualityreport import DataQualityReportForAllProjects
from indigo.models import Fund, Organisation, Project

from .spreadsheetforms import (
    convert_fund_data_to_spreadsheetforms_data,
    convert_organisation_data_to_spreadsheetforms_data,
    convert_project_data_to_spreadsheetforms_data,
)


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
    data = convert_project_data_to_spreadsheetforms_data(project, public_only=True)

    # --- XLSX File
    guide_file = settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
        "spreadsheet_public_form_guide"
    ]

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
    data = convert_organisation_data_to_spreadsheetforms_data(
        organisation, public_only=True
    )

    # --- XLSX File
    guide_file = os.path.join(
        settings.BASE_DIR,
        "indigo",
        "spreadsheetform_guides",
        "organisation_public_v003.xlsx",
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
    data = convert_fund_data_to_spreadsheetforms_data(fund, public_only=True)

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

    _update_public_archive_files_file_per_record_in_zip()
    _update_public_archive_files_file_per_data_type_csv_in_zip()


def _update_public_archive_files_file_per_data_type_csv_in_zip():

    # Create Zip File
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    out_file_zip = file.name
    file.close()
    with ZipFile(out_file_zip, "w") as zipfile:

        # Projects
        _update_public_archive_files_file_per_data_type_csv_in_zip_for_records(
            "projects",
            settings.JSONDATAFERRET_TYPE_INFORMATION["project"]["fields"],
            Project.objects.filter(exists=True, status_public=True).order_by(
                "public_id"
            ),
            zipfile,
        )

        # Organisations
        _update_public_archive_files_file_per_data_type_csv_in_zip_for_records(
            "organisations",
            settings.JSONDATAFERRET_TYPE_INFORMATION["organisation"]["fields"],
            Organisation.objects.filter(exists=True, status_public=True).order_by(
                "public_id"
            ),
            zipfile,
        )

        # Funds
        _update_public_archive_files_file_per_data_type_csv_in_zip_for_records(
            "funds",
            settings.JSONDATAFERRET_TYPE_INFORMATION["fund"]["fields"],
            Fund.objects.filter(exists=True, status_public=True).order_by("public_id"),
            zipfile,
        )

    # Move to Django Storage
    default_storage_name = "public/all_data_per_data_type_csv.zip"
    default_storage.delete(default_storage_name)
    with open(out_file_zip, "rb") as fp:
        default_storage.save(default_storage_name, ContentFile(fp.read()))

    # Delete Temp file
    os.remove(out_file_zip)


def _update_public_archive_files_file_per_data_type_csv_in_zip_for_records(
    type_id, type_information_fields, records, zipfile
):

    # Make list of files to make, and the labels and keys that will be used for each one
    main_file_labels = ["ID"]
    main_file_keys = []
    files_to_make = {}

    for config in type_information_fields:
        if config.get("type", "") != "list" and config.get("key").find("/status") == -1:
            main_file_labels.append(config.get("title"))
            main_file_keys.append(config.get("key"))
        elif config.get("type", "") == "list":
            file_to_make = {
                "list_key": config["key"],
                "labels": ["Project ID"],
                "keys": [],
            }
            for field in config["fields"]:
                if field["key"].find("/status") == -1:
                    file_to_make["labels"].append(field["title"])
                    file_to_make["keys"].append(field["key"])
            files_to_make[config["key"].replace("/", "")] = file_to_make

    # Create main file and add to ZIP
    with io.StringIO() as csv_output:
        writer = csv.writer(csv_output)
        writer.writerow(main_file_labels)
        for record in records:
            # id
            row = [record.public_id]
            # fields
            for key in main_file_keys:
                row.append(jsonpointer.resolve_pointer(record.data_public, key, ""))
            # record done
            writer.writerow(row)
        zipfile.writestr(type_id + ".csv", csv_output.getvalue())

    # Create each sub file and add to ZIP
    for file_to_make_id, file_to_make_config in files_to_make.items():
        with io.StringIO() as csv_output:
            writer = csv.writer(csv_output)
            writer.writerow(file_to_make_config["labels"])
            for record in records:
                row_datas = jsonpointer.resolve_pointer(
                    record.data_public, file_to_make_config["list_key"], []
                )
                if row_datas and isinstance(row_datas, list):
                    for row_data in row_datas:
                        # id
                        row = [record.public_id]
                        # fields
                        for key in file_to_make_config["keys"]:
                            row.append(jsonpointer.resolve_pointer(row_data, key, ""))
                        # record done
                        writer.writerow(row)
            zipfile.writestr(
                type_id + "_" + file_to_make_id + ".csv", csv_output.getvalue()
            )


def _update_public_archive_files_file_per_record_in_zip():

    # Create Temp Files
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    filename = file.name
    file.close()

    # Contents
    with ZipFile(filename, "w") as zipfile_all:

        for organisation in Organisation.objects.filter(
            exists=True, status_public=True
        ):
            _put_file_in_zip_file(
                [zipfile_all],
                "public/organisation/" + organisation.public_id + ".xlsx",
                "organisation/" + organisation.public_id + ".xlsx",
            )

        for fund in Fund.objects.filter(exists=True, status_public=True):
            _put_file_in_zip_file(
                [zipfile_all],
                "public/fund/" + fund.public_id + ".xlsx",
                "fund/" + fund.public_id + ".xlsx",
            )

        for project in Project.objects.filter(exists=True, status_public=True):
            _put_file_in_zip_file(
                [zipfile_all],
                "public/project/" + project.public_id + ".xlsx",
                "project/" + project.public_id + ".xlsx",
            )

    # Move to Django Storage
    default_storage.delete("public/all_data_as_spreadsheets.zip")
    with open(filename, "rb") as fp:
        default_storage.save(
            "public/all_data_as_spreadsheets.zip", ContentFile(fp.read()),
        )

    # Delete Temp file
    os.remove(filename)


def _put_file_in_zip_file(zipfiles, file_name_in_storage, file_name_in_zip):
    if default_storage.exists(file_name_in_storage):
        with default_storage.open(file_name_in_storage, "rb") as fp:
            data = fp.read()
            for zipfile in zipfiles:
                zipfile.writestr(file_name_in_zip, data)


def update_data_quality_report_file_for_all_projects():

    data_quality_report = DataQualityReportForAllProjects()

    # Data
    data = {"single_fields": [], "list_fields": []}

    # Single Field data
    for field in data_quality_report.get_possible_fields_for_single_field_statistics():
        field_data = data_quality_report.get_single_field_statistics_for_field(field)
        field_data["field"] = field
        data["single_fields"].append(field_data)

    # List Field data
    for field in data_quality_report.get_possible_fields_for_list_field_statistics():
        field_data = data_quality_report.get_list_field_statistics_for_field(field)
        field_data["field"] = field
        data["list_fields"].append(field_data)

    # Create in Temp
    guide_file = settings.JSONDATAFERRET_TYPE_INFORMATION["project"][
        "spreadsheet_data_quality_report_public_guide"
    ]
    file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    out_file = file.name
    file.close()
    spreadsheetforms.api.put_data_in_form(guide_file, data, out_file)

    # Move to Django Storage
    default_storage_name_xlsx = "public/project_data_quality_report.xlsx"
    default_storage.delete(default_storage_name_xlsx)
    with open(out_file, "rb") as fp:
        default_storage.save(default_storage_name_xlsx, ContentFile(fp.read()))

    # Delete Temp file
    os.remove(out_file)
