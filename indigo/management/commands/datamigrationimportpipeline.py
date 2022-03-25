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
            for row in csvreader:
                if row[0].strip() or row[3].strip():
                    pipeline_data = {
                        "status": "PRIVATE",
                        "name": {"value": row[3].strip()},
                        "state_development": {
                            "state": {"value": "Current", "status": "PUBLIC"}
                        },
                        "contact": {
                            "name": {"value": row[0].strip(), "status": "PRIVATE"},
                            "email": {"value": row[2].strip(), "status": "PRIVATE"},
                        },
                        "dates": {
                            "expected_launch_date": {
                                "value": row[10].strip(),
                                "status": "PUBLIC",
                            },
                            "expected_development_time": {
                                "value": row[11].strip(),
                                "status": "PUBLIC",
                            },
                            "design_process_began": {
                                "value": row[12].strip(),
                                "status": "PUBLIC",
                            },
                            "expected_length": {
                                "value": row[31].strip(),
                                "status": "PUBLIC",
                            },
                        },
                        "purpose_and_classifications": {
                            "secondary_sdg_goals": {
                                "value": row[8]
                                .strip()
                                .replace("Goal", "")
                                .replace("/", ","),
                                "status": "PUBLIC",
                            },
                            "social_challenge": {
                                "value": row[13].strip(),
                                "status": "PUBLIC",
                            },
                            "intervention": {
                                "value": row[15].strip(),
                                "status": "PUBLIC",
                            },
                            "policy_sector": {
                                "other": {"value": row[7].strip()},
                                "status": "PUBLIC",
                            },
                        },
                        "service_and_beneficiaries": {
                            "target_population": {
                                "value": row[14].strip(),
                                "status": "PUBLIC",
                            },
                            "targeted_number_service_users_or_beneficiaries_total": {
                                "value": row[16].strip(),
                                "status": "PUBLIC",
                            },
                        },
                        "misc2": {
                            "rationale_outcomes_based_financing": {
                                "value": row[19].strip(),
                                "status": "PUBLIC",
                            }
                        },
                        "misc3": {
                            "key_challenges_launch": {
                                "value": row[20].strip(),
                                "status": "PUBLIC",
                            }
                        },
                        "overall_project_finance": {
                            "maximum_potential_outcome_payment_v2": {
                                "amount": {
                                    "value": row[28].strip().replace("€", ""),
                                    "status": "PUBLIC",
                                },
                                "currency": {
                                    "value": row[29].strip(),
                                    "status": "PUBLIC",
                                },
                            }
                        },
                        "misc1": {
                            "type_instrument_project": {
                                "other": {"value": row[4].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "misc4": {
                            "role_domestic_government": {
                                "other": {"value": row[27].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "misc5": {
                            "service_providers_identified_selected": {
                                "other": {"value": row[35].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "misc6": {
                            "feasibility_study": {
                                "value": row[33].strip(),
                                "status": "PUBLIC",
                            }
                        },
                        "misc7": {
                            "proposed_financing_instruments": {
                                "other": {"value": row[32].strip()},
                                "status": "PUBLIC",
                            }
                        },
                        "technical_assistance_grant_development": {
                            "main": {"value": row[34].strip(), "status": "PUBLIC"}
                        },
                        "notes": {"value": row[36].strip(), "status": "PUBLIC"},
                        "delivery_locations": [],
                        "sources": [],
                        "service_provisions": [],
                        "outcome_payment_commitments": [],
                        "investments": [],
                        "intermediary_services": [],
                        "outcome_metrics": [],
                        "documents": [],
                    }

                    if row[1].strip():
                        pipeline_data["intermediary_services"].append(
                            {"notes": row[1].strip(), "status": "PUBLIC"}
                        )

                    if row[5].strip():
                        part_larger_program_bits = row[5].strip().split("-")
                        part_larger_program_bits.append(
                            ""
                        )  # make sure not crash if index 1 not already exist
                        pipeline_data["part_larger_program"] = {
                            "main": {
                                "value": part_larger_program_bits[0].strip(),
                                "status": "PUBLIC",
                            },
                            "details": {
                                "value": part_larger_program_bits[1].strip(),
                                "status": "PUBLIC",
                            },
                        }

                    if row[6].strip():
                        pipeline_data["delivery_locations"].append(
                            {
                                "location_name": {"value": row[6].strip()},
                                # Could try to map to location_country here?
                                "status": "PUBLIC",
                            }
                        )

                    if row[9].strip():
                        stage_dev_bits = row[9].strip().split("-")
                        stage_dev_bits.append(
                            ""
                        )  # make sure not crash if index 1 not already exist
                        pipeline_data["stage_development"] = {
                            "stage": {
                                "value": stage_dev_bits[0].strip(),
                                "status": "PUBLIC",
                            },
                            "notes": stage_dev_bits[1].strip(),
                        }

                    if row[17].strip() or row[18].strip():
                        pipeline_data["outcome_metrics"].append(
                            {
                                "definition": {"value": row[17].strip()},
                                "outcome_validation_method": {"value": row[18].strip()},
                                "status": "PUBLIC",
                            }
                        )

                    if row[21].strip():
                        pipeline_data["outcome_payment_commitments"].append(
                            {"notes": row[21].strip(), "status": "PUBLIC"}
                        )

                    if row[22].strip():
                        pipeline_data["investments"].append(
                            {"notes": row[22].strip(), "status": "PUBLIC"}
                        )

                    if row[23].strip():
                        pipeline_data["service_provisions"].append(
                            {"notes": row[23].strip(), "status": "PUBLIC"}
                        )

                    if row[24].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Evaluator - " + row[24].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    if row[25].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Advisor - " + row[25].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    if row[26].strip():
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Other - " + row[26].strip(),
                                "status": "PUBLIC",
                            }
                        )

                    # TODO Column e 4 2.2 Type of instrument and project (other only currently)
                    # TODO Column h 7 2.5 Sector (other only currently)
                    # TODO Column ab 27 4.7 What is or will be the role of the domestic government? (select all that apply) (other only currently)
                    # TODO Column ag 32 5.5 Proposed financing instruments (select all that apply) (other only currently)
                    # TODO Column aj 35 6.3 How were service providers identified and selected? (other only currently)

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
