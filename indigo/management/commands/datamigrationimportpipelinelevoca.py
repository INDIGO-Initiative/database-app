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
                if row[1].strip() or row[3].strip():
                    pipeline_data = {
                        "status": "PRIVATE",
                        "name": {"value": row[4].strip()},
                        "state_development": {
                            "state": {"value": "Current", "status": "PUBLIC"}
                        },
                        "stage_development": {
                            "stage": {"value": row[12].strip(), "status": "PUBLIC",},
                            "notes": row[13].strip(),
                        },
                        "contact": {
                            "name": {"value": row[1].strip(), "status": "PRIVATE"},
                            "email": {"value": row[3].strip(), "status": "PRIVATE"},
                        },
                        "dates": {
                            "expected_launch_date": {
                                "value": row[14].strip(),
                                "status": "PUBLIC",
                            },
                            "expected_development_time": {
                                "value": row[15].strip(),
                                "status": "PUBLIC",
                            },
                            "design_process_began": {
                                "value": row[16].strip(),
                                "status": "PUBLIC",
                            },
                            "expected_length": {
                                "value": row[38].strip(),
                                "status": "PUBLIC",
                            },
                        },
                        "part_larger_program": {
                            "main": {
                                "value": to_boolean(row[6].strip()),
                                "status": "PUBLIC",
                            },
                            "details": {"value": row[7].strip(), "status": "PUBLIC",},
                        },
                        "purpose_and_classifications": {
                            "secondary_sdg_goals": {
                                "value": row[11].strip(),
                                "status": "PUBLIC",
                            },
                            "social_challenge": {
                                "value": row[17].strip(),
                                "status": "PUBLIC",
                            },
                            "intervention": {
                                "value": row[19].strip(),
                                "status": "PUBLIC",
                            },
                            "policy_sector": {
                                "other": {
                                    "value": row[9].strip() + " " + row[10].strip()
                                },
                                "status": "PUBLIC",
                            },
                        },
                        "service_and_beneficiaries": {
                            "target_population": {
                                "value": row[18].strip(),
                                "status": "PUBLIC",
                            },
                            "targeted_number_service_users_or_beneficiaries_total": {
                                "value": row[20].strip(),
                                "status": "PUBLIC",
                            },
                        },
                        "misc2": {
                            "rationale_outcomes_based_financing": {
                                "value": row[24].strip(),
                                "status": "PUBLIC",
                            }
                        },
                        "misc3": {
                            "key_challenges_launch": {
                                "value": row[25].strip(),
                                "status": "PUBLIC",
                            }
                        },
                        "overall_project_finance": {
                            "maximum_potential_outcome_payment_v2": {
                                "amount": {
                                    "value": row[35].strip(),
                                    "status": "PUBLIC",
                                },
                                "currency": {
                                    "value": row[36].strip(),
                                    "status": "PUBLIC",
                                },
                            }
                        },
                        "misc1": {
                            "type_instrument_project": {
                                "other": {"value": row[5].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "misc4": {
                            "role_domestic_government": {
                                "other": {"value": row[32].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "misc5": {
                            "service_providers_identified_selected": {
                                "other": {
                                    "value": row[44].strip() + " " + row[45].strip()
                                },
                                "status": "PUBLIC",
                            }
                        },
                        "misc6": {
                            "feasibility_study": {
                                "value": to_boolean(row[41].strip()),
                                "status": "PUBLIC",
                            }
                        },
                        "misc7": {
                            "proposed_financing_instruments": {
                                "other": {
                                    "value": row[39].strip() + " " + row[40].strip()
                                },
                                "status": "PUBLIC",
                            }
                        },
                        "technical_assistance_grant_development": {
                            "main": {
                                "value": to_boolean(row[42].strip()),
                                "status": "PUBLIC",
                            },
                            "details": {"value": row[43].strip(), "status": "PUBLIC"},
                        },
                        "notes": {"value": row[46].strip(), "status": "PUBLIC"},
                        "delivery_locations": [],
                        "sources": [],
                        "service_provisions": [],
                        "outcome_payment_commitments": [],
                        "investments": [],
                        "intermediary_services": [],
                        "outcome_metrics": [],
                        "documents": [],
                    }

                    if row[2].strip():
                        pipeline_data["intermediary_services"].append(
                            {"notes": row[2].strip(), "status": "PUBLIC"}
                        )

                    if row[8].strip():
                        pipeline_data["delivery_locations"].append(
                            {
                                "location_name": {"value": row[8].strip()},
                                # Could try to map to location_country here?
                                "status": "PUBLIC",
                            }
                        )

                    if row[21].strip() or row[22].strip() or row[23].strip():
                        pipeline_data["outcome_metrics"].append(
                            {
                                "definition": {"value": row[21].strip()},
                                "outcome_validation_method": {"value": row[22].strip()},
                                "notes": row[23].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    if row[26].strip():
                        pipeline_data["outcome_payment_commitments"].append(
                            {"notes": row[26].strip(), "status": "PUBLIC"}
                        )

                    if row[27].strip():
                        pipeline_data["investments"].append(
                            {"notes": row[27].strip(), "status": "PUBLIC"}
                        )

                    if row[28].strip():
                        pipeline_data["service_provisions"].append(
                            {"notes": row[28].strip(), "status": "PUBLIC"}
                        )

                    if row[29].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Evaluator - " + row[29].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    if row[30].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Advisor - " + row[30].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    if row[31].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Other - " + row[31].strip(),
                                "status": "PUBLIC",
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
