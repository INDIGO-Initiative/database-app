import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


class Command(BaseCommand):
    help = "Data Migration - Clean Country"

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        writes = []

        for project in Project.objects.all():
            print("\nPROJECT " + project.public_id)

            changes = False

            delivery_locations = project.data_private.get("delivery_locations")
            if delivery_locations:
                for delivery_location in delivery_locations:

                    print(
                        "Name= "
                        + str(
                            delivery_location.get("location_name", {}).get("value", "")
                        )
                    )
                    print(
                        "Country= "
                        + str(
                            delivery_location.get("location_country", {}).get(
                                "value", ""
                            )
                        )
                    )
                    country_code = get_country_code_from_old_data(
                        delivery_location.get("location_name", {}).get("value", ""),
                        delivery_location.get("location_country", {}).get("value", ""),
                    )
                    if country_code:
                        print("RESULT Will change country to " + country_code)
                        delivery_location["location_country"]["value"] = country_code
                        changes = True
                    else:
                        print("RESULT will not change")

            if changes:
                writes.append(
                    NewEventData(
                        project.record.type,
                        project.record,
                        {"delivery_locations": delivery_locations},
                        mode=jsondataferret.EVENT_MODE_MERGE,
                        approved=True,
                    )
                )

        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment="Data Migration - Clean Country",
            )


def get_country_code_from_old_data(location_name, location_country):
    if location_name is None:
        location_name = ""
    if location_country is None:
        location_country = ""
    if "Queensland" in location_name or "Queensland" in location_country:
        return "AU"
    if "Manchester" in location_name or "Manchester" in location_country:
        return "GB"
    if "United Kingdom" in location_name or "United Kingdom" in location_country:
        return "GB"
    if "USA" in location_name or "USA" in location_country:
        return "US"
    if "France" in location_name or "France" in location_country:
        return "FR"
    if "South Africa" in location_name or "South Africa" in location_country:
        return "ZA"
    if "Switzerland" in location_name or "Switzerland" in location_country:
        return "CH"
    if (
        "United Arab Emirates" in location_name
        or "United Arab Emirates" in location_country
    ):
        return "AE"
    if (
        "Greater Merseyside" in location_name
        or "Greater Merseyside" in location_country
    ):
        return "GB"
    if "Australia" in location_name or "Australia" in location_country:
        return "AU"
    if "Bristol" in location_name or "Bristol" in location_country:
        return "GB"
    if "London" in location_name or "London" in location_country:
        return "GB"
    if "UK" in location_name or "UK" in location_country:
        return "GB"
    if "West Midlands" in location_name or "West Midlands" in location_country:
        return "GB"
    if "Netherlands" in location_name or "Netherlands" in location_country:
        return "NL"
    if "Austria" in location_name or "Austria" in location_country:
        return "AT"
    if "East Midlands" in location_name or "East Midlands" in location_country:
        return "GB"
    if "India" in location_name or "India" in location_country:
        return "IN"
    if "Auckland" in location_name or "Auckland" in location_country:
        return "NZ"
    if "Portugal" in location_name or "Portugal" in location_country:
        return "PT"
    if "Israel" in location_name or "Israel" in location_country:
        return "IL"
    if "Essex" in location_name or "Essex" in location_country:
        return "GB"
    if "Scotland" in location_name or "Scotland" in location_country:
        return "GB"
    if "Colombia" in location_name or "Colombia" in location_country:
        return "CO"
    if "Finland" in location_name or "Finland" in location_country:
        return "FL"
    if "Hiroshima" in location_name or "Hiroshima" in location_country:
        return "JP"
    if (
        "Newcastle City Council" in location_name
        or "Newcastle City Council" in location_country
    ):
        return "GB"
    if (
        "City of Sunderland" in location_name
        or "City of Sunderland" in location_country
    ):
        return "GB"
    if "Greater Boston" in location_name or "Greater Boston" in location_country:
        return "US"
    if "Palestine" in location_name or "Palestine" in location_country:
        return "PS"
    if "Cameroon" in location_name or "Cameroon" in location_country:
        return "CM"
    if "Argentina" in location_name or "Argentina" in location_country:
        return "AR"
    if "California" in location_name or "California" in location_country:
        return "US"
    if (
        "Newcastle Upon Tyne" in location_name
        or "Newcastle Upon Tyne" in location_country
    ):
        return "GB"
    if "New South Wales" in location_name or "New South Wales" in location_country:
        return "AU"
    if "Wales" in location_name or "Wales" in location_country:
        return "GB"
    if "Russia" in location_name or "Russia" in location_country:
        return "RU"
    if "New York City" in location_name or "New York City" in location_country:
        return "US"
    if "Canada" in location_name or "Canada" in location_country:
        return "CA"
    if "New Zealand" in location_name or "New Zealand" in location_country:
        return "NZ"
    if "Nottingham" in location_name or "Nottingham" in location_country:
        return "GB"
    if "Peterborough" in location_name or "Peterborough" in location_country:
        return "GB"
    if "Birmingham" in location_name or "Birmingham" in location_country:
        return "GB"
    if "Kenya" in location_name or "Kenya" in location_country:
        return "KE"
    if "Peru" in location_name or "Peru" in location_country:
        return "PE"
    if "Belgium" in location_name or "Belgium" in location_country:
        return "BE"
    if "Sweden" in location_name or "Sweden" in location_country:
        return "SE"
    if "Japan" in location_name or "Japan" in location_country:
        return "JP"
    if "Lincolnshire" in location_name or "Lincolnshire" in location_country:
        return "GB"
    if "Yorkshire" in location_name or "Yorkshire" in location_country:
        return "GB"
    if "Thames Valley" in location_name or "Thames Valley" in location_country:
        return "GB"
    if (
        "Inner city Melbourne" in location_name
        or "Inner city Melbourne" in location_country
    ):
        return "AU"
    if "Ohio" in location_name or "Ohio" in location_country:
        return "US"
    if "Chile" in location_name or "Chile" in location_country:
        return "CL"
    if "Cambodia" in location_name or "Cambodia" in location_country:
        return "KH"
    if "Osnabrück" in location_name or "Osnabrück" in location_country:
        return "DE"
    if "Brussels" in location_name or "Brussels" in location_country:
        return "BE"
    if "Cali" in location_name or "Cali" in location_country:
        return "CO"
    if "Liverpool" in location_name or "Liverpool" in location_country:
        return "GB"
    if "South Korea" in location_name or "South Korea" in location_country:
        return "KR"
    return ""
