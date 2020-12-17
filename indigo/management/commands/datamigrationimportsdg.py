import csv

import jsondataferret
from django.core.management.base import BaseCommand
from jsondataferret.pythonapi.newevent import NewEventData, newEvent

from indigo.models import Project


# CSV Columns should be
# 0 - Project ID
# 1 - Outcome Definition
# 2 - Primary SDG Goal
# 3 - Primary SDG Target
# 4 - Secondary SDG goal
# 5 - Secondary SDG target
# 6 - Notes for outcome row
#
# CSV Rows should be all data rows - no header
#
class Command(BaseCommand):
    help = "Data Migration - Import SDG"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        parser.add_argument("import_comment")

    def handle(self, *args, **options):

        # Load all data into groups
        data_grouped = {}
        with open(options["filename"], newline="") as csvfile:
            csvreader = csv.reader(csvfile, delimiter=",", quotechar='"')
            for row in csvreader:
                project_id = row[0]
                outcome_definition = row[1]
                primary_sdg_goal = row[2]
                primary_sdg_target = row[3]
                secondary_sdg_goal = row[4]
                secondary_sdg_target = row[5]
                notes = row[6]
                if project_id and outcome_definition:
                    if project_id not in data_grouped.keys():
                        data_grouped[project_id] = {}
                    if outcome_definition in data_grouped[project_id].keys():
                        raise Exception("Are rows repeated?")
                    data_grouped[project_id][outcome_definition] = {
                        "primary_sdg_goal": parse_goal(primary_sdg_goal),
                        "primary_sdg_target": parse_target(primary_sdg_target),
                        "secondary_sdg_goal": parse_goal(secondary_sdg_goal),
                        "secondary_sdg_target": parse_target(secondary_sdg_target),
                        "notes": notes,
                    }

        # Now Process project at a time, working out writes
        writes = []
        for project_id in data_grouped.keys():
            project = Project.objects.get(public_id=project_id)
            if project:
                writes.extend(self._process_project(project, data_grouped[project_id]))

        # Finally write
        if writes:
            print("Saving")
            newEvent(
                writes, user=None, comment=options["import_comment"],
            )

    def _process_project(self, project, data):

        source_id = "sourcehackandlearn2020"
        source_name = "Hack and Learn - September 2020"

        print("Project " + project.public_id)
        changes_project = False

        # Add to sources
        sources = project.data_private.get("sources", [])
        for existing_sources in sources:
            if source_id == existing_sources.get("id"):
                raise Exception("Source ID already used")
        sources.append(
            {
                "id": source_id,
                "url": {"value": None},
                "name": {"value": source_name},
                "type": {"value": None},
                "archive_url": {"value": None},
                "internal_url": {"value": None},
                "accessed_date": {"value": None},
                "publication_date": {"value": None},
                "publishing_organisation_ids": {"value": None},
            }
        )

        # Look at outcome metrics
        outcome_metrics = project.data_private.get("outcome_metrics", [])
        for outcome_metric in outcome_metrics:
            changes_row = False
            outcome_metric_definition = outcome_metric.get("definition").get("value")
            if outcome_metric_definition in data:
                primary_sdg_goal = data[outcome_metric_definition]["primary_sdg_goal"]
                primary_sdg_target = data[outcome_metric_definition][
                    "primary_sdg_target"
                ]
                secondary_sdg_goal = data[outcome_metric_definition][
                    "secondary_sdg_goal"
                ]
                secondary_sdg_target = data[outcome_metric_definition][
                    "secondary_sdg_target"
                ]
                notes = data[outcome_metric_definition]["notes"]
                if primary_sdg_goal and not outcome_metric.get("primary_sdg_goal").get(
                    "value"
                ):
                    print(
                        ".... Setting primary_sdg_goal to "
                        + primary_sdg_goal
                        + " for outcome: "
                        + outcome_metric_definition[0:20]
                    )
                    outcome_metric["primary_sdg_goal"] = {"value": primary_sdg_goal}
                    changes_project = True
                    changes_row = True
                if primary_sdg_target and not outcome_metric.get(
                    "primary_sdg_target"
                ).get("value"):
                    print(
                        ".... Setting primary_sdg_target to "
                        + primary_sdg_target
                        + " for outcome: "
                        + outcome_metric_definition[0:20]
                    )
                    outcome_metric["primary_sdg_target"] = {"value": primary_sdg_target}
                    changes_project = True
                    changes_row = True
                if secondary_sdg_goal and not outcome_metric.get(
                    "secondary_sdg_goals"
                ).get("value"):
                    print(
                        ".... Setting secondary_sdg_goals to "
                        + secondary_sdg_goal
                        + " for outcome: "
                        + outcome_metric_definition[0:20]
                    )
                    outcome_metric["secondary_sdg_goals"] = {
                        "value": secondary_sdg_goal
                    }
                    changes_project = True
                    changes_row = True
                if secondary_sdg_target and not outcome_metric.get(
                    "secondary_sdg_targets"
                ).get("value"):
                    print(
                        ".... Setting secondary_sdg_targets to "
                        + secondary_sdg_target
                        + " for outcome: "
                        + outcome_metric_definition[0:20]
                    )
                    outcome_metric["secondary_sdg_targets"] = {
                        "value": secondary_sdg_target
                    }
                    changes_project = True
                    changes_row = True
                if changes_row:
                    if outcome_metric.get("source_ids"):
                        outcome_metric["source_ids"] += ", " + source_id
                    else:
                        outcome_metric["source_ids"] = source_id
                    if notes:
                        print(" .... .... and adding note: " + notes)
                        if outcome_metric.get("notes"):
                            outcome_metric["notes"] += "\n\n" + notes
                        else:
                            outcome_metric["notes"] = notes

        # Write if needed
        if changes_project:
            return [
                NewEventData(
                    project.record.type,
                    project.record,
                    {"outcome_metrics": outcome_metrics},
                    mode=jsondataferret.EVENT_MODE_MERGE,
                    approved=True,
                ),
                NewEventData(
                    project.record.type,
                    project.record,
                    {"sources": sources},
                    mode=jsondataferret.EVENT_MODE_MERGE,
                    approved=True,
                ),
            ]
        else:
            return []


def parse_goal(goal):
    if goal.startswith("GOAL "):
        goal = goal[5:]
    goal_bits = goal.strip().split(":")
    return goal_bits[0]


def parse_target(target):
    target_bits = target.split(" ")
    return target_bits[0]
