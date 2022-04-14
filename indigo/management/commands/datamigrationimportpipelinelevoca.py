import csv

from django.core.management.base import BaseCommand
from jsondataferret.models import Type
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo import TYPE_PIPELINE_PUBLIC_ID

DELIVERY_LOCATION_COLUMNS_TO_COUNTRY_CODE = {
    21: "AM",
    22: "BD",
    23: "BF",
    24: "KH",
    25: "CO",
    26: "CI",
    27: "SV",
    28: "ET",
    29: "HT",
    30: "HN",
    31: "IN",
    32: "ID",
    33: "JO",
    34: "KE",
    35: "LB",
    36: "LS",
    37: "MX",
    38: "MZ",
    39: "NA",
    40: "NP",
    41: "NE",
    42: "NG",
    43: "PK",
    44: "SN",
    45: "TZ",
    46: "VN",
    47: "",
}


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
                            "stage": {"value": row[83], "status": "PUBLIC",},
                            "notes": row[84],
                            "source_ids": ("source1" if row[83] or row[84] else ""),
                        },
                        "contact": {
                            "name": {"value": row[1], "status": "PRIVATE"},
                            "email": {"value": row[3], "status": "PRIVATE"},
                        },
                        "dates": {
                            "expected_launch_date": {
                                "value": row[85],
                                "status": "PUBLIC",
                            },
                            "expected_development_time": {
                                "value": row[86],
                                "status": "PUBLIC",
                            },
                            "design_process_began": {
                                "value": row[87],
                                "status": "PUBLIC",
                            },
                            "expected_length": {"value": row[124], "status": "PUBLIC",},
                            "source_ids": (
                                "source1"
                                if row[85] or row[86] or row[87] or row[124]
                                else ""
                            ),
                        },
                        "part_larger_program": {
                            "main": {"value": to_boolean(row[11]), "status": "PUBLIC",},
                            "details": {"value": row[12], "status": "PUBLIC",},
                            "source_ids": ("source1" if row[11] or row[12] else ""),
                        },
                        "purpose_and_classifications": {
                            "secondary_sdg_goals": {
                                "value": row[65],
                                "status": "PUBLIC",
                            },
                            "social_challenge": {"value": row[88], "status": "PUBLIC",},
                            "intervention": {"value": row[90], "status": "PUBLIC",},
                            "policy_sector": {
                                "employment_and_private_sector_development": {
                                    "value": to_boolean(row[56])
                                },
                                "education": {"value": to_boolean(row[55])},
                                "social_protection": {"value": to_boolean(row[61])},
                                # "criminal_justice": { "value": to_boolean(row[]) },
                                "health": {"value": to_boolean(row[59])},
                                "agriculture": {"value": to_boolean(row[54])},
                                "environment_and_climate_change": {
                                    "value": to_boolean(row[58])
                                },
                                "water_sanitation_hygiene": {
                                    "value": to_boolean(row[62])
                                },
                                "energy": {"value": to_boolean(row[57])},
                                "humanitarian": {"value": to_boolean(row[60])},
                                "other": {"value": row[64]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1"),
                        },
                        "service_and_beneficiaries": {
                            "target_population": {
                                "value": row[89],
                                "status": "PUBLIC",
                            },
                            "targeted_number_service_users_or_beneficiaries_total": {
                                "value": row[91],
                                "status": "PUBLIC",
                            },
                            "country_classification": {
                                "low_income": {"value": to_boolean(row[52])},
                                "lower_middle_income": {"value": to_boolean(row[51])},
                                "upper_middle_income": {"value": to_boolean(row[50])},
                                "high_income": {"value": to_boolean(row[49])},
                            },
                            "source_ids": ("source1"),
                        },
                        "misc2": {
                            "rationale_outcomes_based_financing": {
                                "value": row[101],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[101] else ""),
                        },
                        "misc3": {
                            "key_challenges_launch": {
                                "value": row[102],
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[102] else ""),
                        },
                        "overall_project_finance": {
                            "maximum_potential_outcome_payment_v2": {
                                "amount": {"value": row[119], "status": "PUBLIC",},
                                "currency": {"value": row[121], "status": "PUBLIC",},
                            },
                            "source_ids": ("source1" if row[119] or row[121] else ""),
                        },
                        "misc1": {
                            "type_instrument_project": {
                                "impact_bond": {"value": to_boolean(row[6])},
                                "social_impact_guarantee": {
                                    "value": to_boolean(row[8])
                                },
                                "payment_by_results_no_prefinancing": {
                                    "value": to_boolean(row[7])
                                },
                                "other": {"value": row[10]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1"),
                        },
                        "misc4": {
                            "role_domestic_government": {
                                "outcomes_funder": {"value": to_boolean(row[111])},
                                "service_provider": {"value": to_boolean(row[112])},
                                "member_project_committee": {
                                    "value": to_boolean(row[110])
                                },
                                "no_formal_role": {"value": to_boolean(row[113])},
                                "other": {"value": row[116]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1"),
                        },
                        "misc5": {
                            "service_providers_identified_selected": {
                                "request_for_proposals": {
                                    "value": to_boolean(row[138])
                                },
                                "direct_contracting": {"value": to_boolean(row[139])},
                                "provider_led_development": {
                                    "value": to_boolean(row[137])
                                },
                                "other": {"value": row[141]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1"),
                        },
                        "misc6": {
                            "feasibility_study": {
                                "value": to_boolean(row[133]),
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1" if row[133] else ""),
                        },
                        "misc7": {
                            "proposed_financing_instruments": {
                                "debt": {"value": to_boolean(row[127])},
                                "equity": {"value": to_boolean(row[128])},
                                "guarantee": {"value": to_boolean(row[129])},
                                "grant": {"value": to_boolean(row[126])},
                                "other": {"value": row[132]},
                                "status": "PUBLIC",
                            },
                            "source_ids": ("source1"),
                        },
                        "technical_assistance_grant_development": {
                            "main": {
                                "value": to_boolean(row[134]),
                                "status": "PUBLIC",
                            },
                            "details": {"value": row[135], "status": "PUBLIC"},
                            "source_ids": ("source1" if row[134] or row[135] else ""),
                        },
                        "notes": {"value": row[142], "status": "PUBLIC"},
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

                        for (
                            column_idx,
                            country_code,
                        ) in DELIVERY_LOCATION_COLUMNS_TO_COUNTRY_CODE.items():
                            if row[column_idx].strip() == "1":
                                pipeline_data["delivery_locations"].append(
                                    {
                                        "location_name": {"value": row[20]},
                                        "location_country": {"value": country_code},
                                        "notes": row[48],
                                        "status": "PUBLIC",
                                        "source_ids": "source1",
                                    }
                                )

                    if row[94] or row[95] or row[100]:
                        pipeline_data["outcome_metrics"].append(
                            {
                                "definition": {"value": row[95]},
                                "outcome_validation_method": {"value": row[95]},
                                "notes": row[100],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[103]:
                        pipeline_data["outcome_payment_commitments"].append(
                            {
                                "notes": row[103],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[104]:
                        pipeline_data["investments"].append(
                            {
                                "notes": row[104],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[105]:
                        pipeline_data["service_provisions"].append(
                            {
                                "notes": row[105],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[106]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Evaluator - " + row[106],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[107]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Advisor - " + row[107],
                                "status": "PUBLIC",
                                "source_ids": "source1",
                            }
                        )

                    if row[108]:
                        pipeline_data["intermediary_services"].append(
                            {
                                "organisation_role_category": {"value": "Other"},
                                "notes": "Other - " + row[108],
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
    if input.strip().lower().startswith("y") or input.strip().lower().startswith("1"):
        return "Yes"
    elif input.strip().lower().startswith("n") or input.strip().lower().startswith("0"):
        return "No"
    else:
        return input
