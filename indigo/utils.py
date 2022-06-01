import re

import openpyxl
from jsondataferret.models import Record

from indigo import ID_PREFIX_BY_TYPE


def get_project_spreadsheet_version(filename):
    return _get_spreadsheet_version(filename)


def get_organisation_spreadsheet_version(filename):
    return _get_spreadsheet_version(filename)


def _get_spreadsheet_version(filename):
    workbook = openpyxl.load_workbook(filename, read_only=True)
    worksheet = workbook["Introduction"]
    for row_idx in range(1, worksheet.max_row + 1):
        if worksheet["A" + str(row_idx)].value == "SPREADSHEET VERSION":
            return worksheet["A" + str(row_idx + 1)].value
    return None


def get_next_record_id(type):
    prefix = ID_PREFIX_BY_TYPE[type.public_id]
    last_record = Record.objects.filter(type=type).order_by("-public_id").first()
    if last_record:
        m = re.search(f"^{prefix}([0-9][0-9][0-9][0-9])$", last_record.public_id)
        assert (
            m
        ), f'The record ID "{last_record.public_id}" doesn\'t match the expected template.'
        id_number = int(m.group(1)) + 1
    else:
        id_number = 1

    return f"{prefix}{id_number:04d}"
