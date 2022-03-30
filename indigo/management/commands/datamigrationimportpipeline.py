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
                # "-" is used as a placeholder for no value, and it's never a valid value in itself
                row = [i.strip("-").strip() for i in row]
                if row[0] or row[3]:
                    pipeline_data = {
                        "status": "PRIVATE",
                        "name": {"value": row[3]},
                        "state_development": {
                            "state": {"value": "Current", "status": "PUBLIC"},
                            "source_ids": "source1",
                        },
                        "contact": {
                            "name": {"value": row[0], "status": "PRIVATE"},
                            "email": {"value": row[2], "status": "PRIVATE"},
                        },
                        "dates": {
                            "expected_launch_date": {
                                "value": row[10],
                                "status": "PUBLIC",
                            },
                            "expected_development_time": {
                                "value": row[11],
                                "status": "PUBLIC",
                            },
                            "design_process_began": {
                                "value": row[12],
                                "status": "PUBLIC",
                            },
                            "expected_length": {"value": row[31], "status": "PUBLIC",},
                            "source_ids": (
                                "source1"
                                if row[10] or row[11] or row[12] or row[31]
                                else ""
                            ),
                        },
                        "purpose_and_classifications": {
                            "secondary_sdg_goals": {
                                "value": row[8].replace("Goal", "").replace("/", ","),
                                "status": "PUBLIC",
                            },
                            "social_challenge": {"value": row[13], "status": "PUBLIC",},
                            "intervention": {"value": row[15], "status": "PUBLIC",},
                            "policy_sector": {
                                "other": {"value": row[7]},
                                "status": "PUBLIC",
                            },
                            "source_ids": (
                                "source1"
                                if row[8] or row[13] or row[15] or row[17]
                                else ""
                            ),
                        },
                        "service_and_beneficiaries": {
                            "target_population": {
                                "value": row[14],
                                "status": "PUBLIC",
                            },
                            "targeted_number_service_users_or_beneficiaries_total": {
                                "value": row[16],
                                "status": "PUBLIC",
                            },
                            "country_classification": {
                                "high_income": {"value": "Yes"},
                                "status": "PUBLIC",
                            },
                            "source_ids": "source1",
                        },
                        "misc2": {
                            "rationale_outcomes_based_financing": {
                                "value": row[19],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[19] else ""),
                        },
                        "misc3": {
                            "key_challenges_launch": {
                                "value": row[20],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[20] else ""),
                        },
                        "overall_project_finance": {
                            "maximum_potential_outcome_payment_v2": {
                                "amount": {
                                    "value": row[28].replace("€", ""),
                                    "status": "PUBLIC",
                                },
                                "currency": {"value": row[29], "status": "PUBLIC",},
                            },
                            "source_ids": ("source1" if row[28] or row[29] else ""),
                        },
                        "misc1": {
                            "type_instrument_project": {
                                "other": {"value": row[4]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[4] else ""),
                        },
                        "misc4": {
                            "role_domestic_government": {
                                "other": {"value": row[27]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[27] else ""),
                        },
                        "misc5": {
                            "service_providers_identified_selected": {
                                "other": {"value": row[35]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[35] else ""),
                        },
                        "misc6": {
                            "feasibility_study": {
                                "value": row[33],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[33] else ""),
                        },
                        "misc7": {
                            "proposed_financing_instruments": {
                                "other": {"value": row[32]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[32] else ""),
                        },
                        "technical_assistance_grant_development": {
                            "main": {"value": row[34], "status": "PUBLIC"},
                            "source_ids": ("source1" if row[34] else ""),
                        },
                        "notes": {"value": row[36], "status": "PUBLIC"},
                        "delivery_locations": [],
                        "sources": [
                            {
                                "id": "source1",
                                "name": {
                                    "value": "Data shared by key stakeholders of the project through March 2022 GO Lab questionnaire"
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

                    if row[1]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "notes": row[1],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[5]:
                        part_larger_program_bits = row[5].split("-")
                        part_larger_program_bits.append(
                            ""
                        )  # make sure not crash if index 1 not already exist
                        pipeline_data["part_larger_program"] = {
                            "main": {
                                "value": part_larger_program_bits[0],
                                "status": "PUBLIC",
                            },
                            "details": {
                                "value": part_larger_program_bits[1],
                                "status": "PUBLIC",
                            },
                            "source_ids": "source1",
                        }

                    if row[6]:
                        pipeline_data["delivery_locations"].append(
                            {
                                "location_name": {"value": row[6]},
                                # Could try to map to location_country here?
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[9]:
                        stage_dev_bits = row[9].split("-")
                        stage_dev_bits.append(
                            ""
                        )  # make sure not crash if index 1 not already exist
                        pipeline_data["stage_development"] = {
                            "stage": {"value": stage_dev_bits[0], "status": "PUBLIC",},
                            "notes": stage_dev_bits[1],
                            "source_ids": "source1",
                        }

                    if row[17] or row[18]:
                        pipeline_data["outcome_metrics"].append(
                            {
                                "definition": {"value": row[17]},
                                "outcome_validation_method": {"value": row[18]},
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[21]:
                        pipeline_data["outcome_payment_commitments"].append(
                            {
                                "notes": row[21],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[22]:
                        pipeline_data["investments"].append(
                            {
                                "notes": row[22],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[23]:
                        pipeline_data["service_provisions"].append(
                            {
                                "notes": row[23],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[24]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Evaluator - " + row[24],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[25]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Advisor - " + row[25],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[26]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Other - " + row[26],
                                "status": "PUBLIC",
                                "source_ids": "source1",
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
