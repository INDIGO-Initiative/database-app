import csv

from django.core.management.base import BaseCommand
from jsondataferret.models import Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo import TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID


class Command(BaseCommand):
    help = "Data Migration - Import Assessment Resources"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("import_comment")

    def handle(self, *args, **options):

        type = Type.objects.get(public_id=TYPE_ASSESSMENT_RESOURCE_PUBLIC_ID)

        writes = []
        next_id = 1
        with open(options["filename"], newline="") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=",", quotechar='"')
            for row in csvreader:
                if row[0].strip() and row[17] != "No":
                    row_split = {}
                    for i in range(1, 11):
                        row_split[i] = [
                            s.strip() for s in row[i].split(",") if s.strip()
                        ]

                    assessement_resource_data = {
                        "status": "PUBLIC",
                        "name": {"value": row[0].strip()},
                        "who": {
                            "public_sector": (
                                "YES" if "Public Sector" in row_split[1] else "NO"
                            ),
                            "private_sector": (
                                "YES" if "Private Sector" in row_split[1] else "NO"
                            ),
                            "third_sector": (
                                "YES" if "Third Sector" in row_split[1] else "NO"
                            ),
                        },
                        "output_format": {
                            "agnostic": ("YES" if "Agnostic" in row_split[2] else "NO"),
                            "monetary_valuation": (
                                "YES" if "Monetary Valuation" in row_split[2] else "NO"
                            ),
                            "non_monetary_quant_index": (
                                "YES"
                                if "Non-monetary quant index" in row_split[2]
                                else "NO"
                            ),
                            "ordinal": (
                                "YES"
                                if "Ordinal but not quant" in row_split[2]
                                else "NO"
                            ),
                            "qualitative_only": (
                                "YES" if "Qualitative only" in row_split[2] else "NO"
                            ),
                            "quant_but_no_index": (
                                "YES" if "Quant but no index" in row_split[2] else "NO"
                            ),
                        },
                        "time_frame": {
                            "ongoing": ("YES" if "Ongoing" in row_split[3] else "NO"),
                            "prospective": (
                                "YES" if "Prospective" in row_split[3] else "NO"
                            ),
                            "retrospective": (
                                "YES" if "Retrospective" in row_split[3] else "NO"
                            ),
                        },
                        "scale": {
                            "agnostic": ("YES" if "Agnostic" in row_split[4] else "NO"),
                            "micro": ("YES" if "Micro" in row_split[4] else "NO"),
                            "meso": ("YES" if "Meso" in row_split[4] else "NO"),
                            "macro": ("YES" if "Macro" in row_split[4] else "NO"),
                        },
                        "impact_goal": {
                            "agnostic": ("YES" if "Agnostic" in row_split[5] else "NO"),
                            "defence": ("YES" if "Defence" in row_split[5] else "NO"),
                            "democracy": (
                                "YES" if "Democracy" in row_split[5] else "NO"
                            ),
                            "development_poverty_reduction": (
                                "YES"
                                if "Development/ Poverty Reduction" in row_split[5]
                                or "Microfinance" in row_split[5]
                                else "NO"
                            ),
                            "education": (
                                "YES" if "Education" in row_split[5] else "NO"
                            ),
                            "employment_financial_well_being": (
                                "YES"
                                if "Employment/ Financial well-being" in row_split[5]
                                else "NO"
                            ),
                            "health": ("YES" if "Health" in row_split[5] else "NO"),
                            "housing": ("YES" if "Housing" in row_split[5] else "NO"),
                            "local_rejuvenation": (
                                "YES" if "Local rejuvenation" in row_split[5] else "NO"
                            ),
                            "sdg_oriented": ("YES" if "SDGs" in row_split[5] else "NO"),
                            "social_impact": (
                                "YES"
                                if "Social impact" in row_split[5]
                                or "SIBs" in row_split[5]
                                else "NO"
                            ),
                            "sustainability_eco": (
                                "YES" if "Sustainability/ Eco" in row_split[5] else "NO"
                            ),
                            "well_being": (
                                "YES" if "Well-being" in row_split[5] else "NO"
                            ),
                        },
                        "type": {
                            "case_study": (
                                "YES"
                                if "Case Study/ Proprietary In-House/ Example Model"
                                in row_split[6]
                                else "NO"
                            ),
                            "classification": (
                                "YES" if "Category" in row_split[6] else "NO"
                            ),
                            "consultancy": (
                                "YES" if "Evaluator" in row_split[6] else "NO"
                            ),
                            "framework": (
                                "YES" if "Framework" in row_split[6] else "NO"
                            ),
                            "guide": ("YES" if "Guide" in row_split[6] else "NO"),
                            "dataset": (
                                "YES"
                                if "Indicators/ Valuations/ Data" in row_split[6]
                                else "NO"
                            ),
                            "principles": (
                                "YES" if "Principles" in row_split[6] else "NO"
                            ),
                            "reporting_standards": (
                                "YES" if "Reporting Standards" in row_split[6] else "NO"
                            ),
                            "resource_repository_or_summary": (
                                "YES"
                                if "Resource Repository or Summary" in row_split[6]
                                else "NO"
                            ),
                            "tool": ("YES" if "Tool" in row_split[6] else "NO"),
                            "training_programme": (
                                "YES" if "Training Programme" in row_split[6] else "NO"
                            ),
                        },
                        "sourcing": {
                            "agnostic": ("YES" if "Agnostic" in row_split[7] else "NO"),
                            "outsource_to_vendor": (
                                "YES" if "Outsource to Vendor" in row_split[7] else "NO"
                            ),
                            "paid_tool": (
                                "YES" if "Paid tool" in row_split[7] else "NO"
                            ),
                            "proprietary_in_house": (
                                "YES"
                                if "Proprietary in-house" in row_split[7]
                                else "NO"
                            ),
                            "self_driven": (
                                "YES" if "Self-driven" in row_split[7] else "NO"
                            ),
                        },
                        "method": {
                            "attribution": (
                                "YES" if "Attribution" in row_split[8] else "NO"
                            ),
                            "diff_in_diff_statistical_analysis": (
                                "YES"
                                if "Diff-in-Diff statistical analysis" in row_split[8]
                                else "NO"
                            ),
                            "ex_ante_projections": (
                                "YES" if "Ex-ante projections" in row_split[8] else "NO"
                            ),
                            "focus_groups": (
                                "YES" if "Focus Groups" in row_split[8] else "NO"
                            ),
                            "framework_agnostic": (
                                "YES" if "Framework agnostic" in row_split[8] else "NO"
                            ),
                            "interviews": (
                                "YES" if "Interviews" in row_split[8] else "NO"
                            ),
                            "mission_alignment": (
                                "YES" if "Mission Alignment" in row_split[8] else "NO"
                            ),
                            "observation": (
                                "YES" if "Observation" in row_split[8] else "NO"
                            ),
                            "operational_data": (
                                "YES" if "Operational Data" in row_split[8] else "NO"
                            ),
                            "rcts": ("YES" if "RCTs" in row_split[8] else "NO"),
                            "surveys": ("YES" if "Surveys" in row_split[8] else "NO"),
                            "theory_of_change": (
                                "YES" if "Theory of Change" in row_split[8] else "NO"
                            ),
                            "before_and_after": "NO",
                        },
                        "used_in_sectors": {
                            "charity": ("YES" if "Charity" in row_split[9] else "NO"),
                            "csr": ("YES" if "CSR" in row_split[9] else "NO"),
                            "development": (
                                "YES" if "Development" in row_split[9] else "NO"
                            ),
                            "governance_policy": (
                                "YES" if "Governance/ Policy" in row_split[9] else "NO"
                            ),
                            "green_book": (
                                "YES" if "Green Book" in row_split[9] else "NO"
                            ),
                            "healthcare": (
                                "YES" if "Healthcare" in row_split[9] else "NO"
                            ),
                            "housing": ("YES" if "Housing" in row_split[9] else "NO"),
                            "igos": ("YES" if "IGOs" in row_split[9] else "NO"),
                            "impact_investing": (
                                "YES" if "Impact investing" in row_split[9] else "NO"
                            ),
                            "microfinance": (
                                "YES" if "Microfinance" in row_split[9] else "NO"
                            ),
                            "sibs": ("YES" if "SIBs" in row_split[9] else "NO"),
                            "social_enterprises": (
                                "YES" if "Social Enterprises" in row_split[9] else "NO"
                            ),
                            "sustainability_eco": (
                                "YES" if "Sustainability/ Eco" in row_split[9] else "NO"
                            ),
                            "developed_countries": (
                                "YES" if "Wealthy Countries" in row_split[9] else "NO"
                            ),
                            "developing_countries": "NO",
                        },
                        "internal_external": {
                            "internal": (
                                "YES" if "Internal" in row_split[10] else "NO"
                            ),
                            "external": (
                                "YES" if "External" in row_split[10] else "NO"
                            ),
                        },
                        "leader": {"value": row[11]},
                        "purpose": {"value": row[12]},
                        "content": {"value": row[13]},
                        "link": {"value": row[14]},
                    }

                    writes.append(
                        NewEventData(
                            type,
                            "INDIGO-ARES-{:04d}".format(next_id),
                            assessement_resource_data,
                            approved=True,
                        )
                    )
                    next_id += 1

        # Finally write
        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment=options["import_comment"],
            )
