import re

import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


class Command(BaseCommand):
    help = "Data Migration - Clean Dates"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        writes = []

        for project in Project.objects.all():
            print("\nPROJECT " + project.public_id)

            changes = False
            dates = project.data_private.get("dates", {})

            for field in [
                "outcomes_contract_signed",
                "contracts_between_all_parties_signed",
                "anticipated_completion_date",
                "actual_completion_date",
                "start_date_of_service_provision",
                "anticipated_end_date_of_service_provision",
                "actual_end_date_of_service_provision",
            ]:

                current_value = dates.get(field).get("value", "")

                print(field + " = " + str(current_value))

                if isinstance(current_value, str):
                    new_value = get_date_from_old_data(current_value)
                    if isinstance(new_value, str):
                        changes = True
                        dates[field]["value"] = new_value
                        print("WILL CHANGE TO: " + new_value)

            if changes:
                writes.append(
                    NewEventData(
                        project.record.type,
                        project.record,
                        {"dates": dates},
                        mode=jsondataferret.EVENT_MODE_MERGE,
                        approved=True,
                    )
                )

        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment="Data Migration - Clean Dates",
            )


def get_date_from_old_data(old_date):
    # 23/06/2015
    m = re.search("^([0-9][0-9])\/([0-9][0-9])\/([0-9][0-9][0-9][0-9])$", old_date)
    if m:
        return m.group(3) + "-" + m.group(2) + "-" + m.group(1)

    # 23/6/2015
    m = re.search("^([0-9][0-9])\/([0-9])\/([0-9][0-9][0-9][0-9])$", old_date)
    if m:
        return m.group(3) + "-0" + m.group(2) + "-" + m.group(1)

    # DD/2/2016
    m = re.search("^DD\/([0-9])\/([0-9][0-9][0-9][0-9])$", old_date)
    if m:
        return m.group(2) + "-0" + m.group(1)

    # DD/09/2015
    m = re.search("^DD\/([0-9][0-9])\/([0-9][0-9][0-9][0-9])$", old_date)
    if m:
        return m.group(2) + "-" + m.group(1)

    # DD/07/16
    m = re.search("^DD\/([0-9][0-9])\/([0-9][0-9])$", old_date)
    if m:
        return "20" + m.group(2) + "-" + m.group(1)

    # DD/MM/2016, dd/mm/2017
    m = re.search("^[dD][dD]\/[mM][mM]\/([0-9][0-9][0-9][0-9])$", old_date)
    if m:
        return m.group(1)

    #    07/01/2014 [January]
    m = re.search("^([0-9][0-9])\/01\/([0-9][0-9][0-9][0-9]) \[January\]$", old_date)
    if m:
        return m.group(2) + "-01-" + m.group(1)

    for month_as_number, month_as_str in [
        ("01", "January"),
        ("02", "February"),
        ("03", "March"),
        ("04", "April"),
        ("05", "May"),
        ("06", "June"),
        ("07", "July"),
        ("08", "August"),
        ("09", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    ]:
        # January 2019
        m = re.search("^" + month_as_str + " ([0-9][0-9][0-9][0-9])$", old_date)
        if m:
            return m.group(1) + "-" + month_as_number

        # 26 November 2015
        m = re.search(
            "^([0-9][0-9]) " + month_as_str + " ([0-9][0-9][0-9][0-9])$", old_date
        )
        if m:
            return m.group(2) + "-" + month_as_number + "-" + m.group(1)

    # just clear these ones
    if old_date == "DD/MM/YYYY":
        return ""

    # Fail
    return None
