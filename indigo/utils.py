import openpyxl


def get_project_spreadsheet_version(filename):
    workbook = openpyxl.load_workbook(filename, read_only=True)
    worksheet = workbook["Introduction"]
    for row_idx in range(1, worksheet.max_row + 1):
        if worksheet["A" + str(row_idx)].value == "SPREADSHEET VERSION":
            return worksheet["A" + str(row_idx + 1)].value
