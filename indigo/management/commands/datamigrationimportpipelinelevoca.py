import csv

from django.core.management.base import BaseCommand
from jsondataferret.models import Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo import TYPE_PIPELINE_PUBLIC_ID


class Command(BaseCommand):
    help = "Data Migration - Import Pipeline"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("first_id_number")
        parser.add_argument("import_comment")

    def handle(self, *args, **options):

        type = Type.objects.get(public_id=TYPE_PIPELINE_PUBLIC_ID)

        writes = []
        next_id = int(options["first_id_number"])
        with open(options["filename"], newline="") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=",", quotechar='"')
            # header rows
            next(csvreader)
            next(csvreader)
            next(csvreader)
            for row in csvreader:
                # "-" is used as a placeholder for no value, and it's never a valid value in itself
                row = [i.strip("-").strip() for i in row]
                if row[1] or row[3]:
                    pipeline_data = {
                        "status": "PRIVATE",
                        "name": {"value": row[4]},
                        "state_development": {
                            "state": {"value": "Current", "status": "PUBLIC"},
                            "source_ids": "source1",
                        },
                        "stage_development": {
                            "stage": {"value": row[12], "status": "PUBLIC",},
                            "notes": row[13],
                            "source_ids": ("source1" if row[12] or row[13] else ""),
                        },
                        "contact": {
                            "name": {"value": row[1], "status": "PRIVATE"},
                            "email": {"value": row[3], "status": "PRIVATE"},
                        },
                        "dates": {
                            "expected_launch_date": {
                                "value": row[14],
                                "status": "PUBLIC",
                            },
                            "expected_development_time": {
                                "value": row[15],
                                "status": "PUBLIC",
                            },
                            "design_process_began": {
                                "value": row[16],
                                "status": "PUBLIC",
                            },
                            "expected_length": {"value": row[38], "status": "PUBLIC",},
                            "source_ids": (
                                "source1"
                                if row[14] or row[15] or row[16] or row[38]
                                else ""
                            ),
                        },
                        "part_larger_program": {
                            "main": {"value": to_boolean(row[6]), "status": "PUBLIC",},
                            "details": {"value": row[7], "status": "PUBLIC",},
                            "source_ids": ("source1" if row[6] or row[7] else ""),
                        },
                        "purpose_and_classifications": {
                            "secondary_sdg_goals": {
                                "value": row[11],
                                "status": "PUBLIC",
                            },
                            "social_challenge": {"value": row[17], "status": "PUBLIC",},
                            "intervention": {"value": row[19], "status": "PUBLIC",},
                            "policy_sector": {
                                "other": {"value": row[9] + " " + row[10]},
                                "status": "PUBLIC",
                            },
                            "source_ids": (
                                "source1"
                                if row[11] or row[17] or row[19] or row[9] or row[10]
                                else ""
                            ),
                        },
                        "service_and_beneficiaries": {
                            "target_population": {
                                "value": row[18],
                                "status": "PUBLIC",
                            },
                            "targeted_number_service_users_or_beneficiaries_total": {
                                "value": row[20],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[18] or row[20] else ""),
                        },
                        "misc2": {
                            "rationale_outcomes_based_financing": {
                                "value": row[24],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[24] else ""),
                        },
                        "misc3": {
                            "key_challenges_launch": {
                                "value": row[25],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[25] else ""),
                        },
                        "overall_project_finance": {
                            "maximum_potential_outcome_payment_v2": {
                                "amount": {"value": row[35], "status": "PUBLIC",},
                                "currency": {"value": row[36], "status": "PUBLIC",},
                            },
                            "source_ids": ("source1" if row[35] or row[36] else ""),
                        },
                        "misc1": {
                            "type_instrument_project": {
                                "other": {"value": row[5]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[5] else ""),
                        },
                        "misc4": {
                            "role_domestic_government": {
                                "other": {"value": row[32]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[32] else ""),
                        },
                        "misc5": {
                            "service_providers_identified_selected": {
                                "other": {"value": row[44] + " " + row[45]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[44] or row[45] else ""),
                        },
                        "misc6": {
                            "feasibility_study": {
                                "value": to_boolean(row[41]),
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[41] else ""),
                        },
                        "misc7": {
                            "proposed_financing_instruments": {
                                "other": {"value": row[39] + " " + row[40]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[39] or row[40] else ""),
                        },
                        "technical_assistance_grant_development": {
                            "main": {"value": to_boolean(row[42]), "status": "PUBLIC",},
                            "details": {"value": row[43], "status": "PUBLIC"},
                            "source_ids": ("source1" if row[43] else ""),
                        },
                        "notes": {"value": row[46], "status": "PUBLIC"},
                        "delivery_locations": [],
                        "sources": [
                            {
                                "id": "source1",
                                "name": {
                                    "value": "Data shared by key stakeholders of the project through March 2022 Levoca questionnaire"
                                },
                            }
                        ],
                        "service_provisions": [],
                        "outcome_payment_commitments": [],
                        "investments": [],
                        "intermediary_services": [],
                        "outcome_metrics": [],
                        "documents": [],
                    }

                    if row[2]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "notes": row[2],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[8]:
                        pipeline_data["delivery_locations"].append(
                            {
                                "location_name": {"value": row[8]},
                                # Could try to map to location_country here?
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[21] or row[22] or row[23]:
                        pipeline_data["outcome_metrics"].append(
                            {
                                "definition": {"value": row[21]},
                                "outcome_validation_method": {"value": row[22]},
                                "notes": row[23],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[26]:
                        pipeline_data["outcome_payment_commitments"].append(
                            {
                                "notes": row[26],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[27]:
                        pipeline_data["investments"].append(
                            {
                                "notes": row[27],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[28]:
                        pipeline_data["service_provisions"].append(
                            {
                                "notes": row[28],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[29]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Evaluator - " + row[29],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[30]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Advisor - " + row[30],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[31]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Other - " + row[31],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    writes.append(
                        NewEventData(
                            type,
                            "INDIGO-PL-{:04d}".format(next_id),
                            pipeline_data,
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


def to_boolean(input):
    if input.lower().startswith("y"):
        return "Yes"
    elif input.lower().startswith("n"):
        return "No"
    else:
        return input
