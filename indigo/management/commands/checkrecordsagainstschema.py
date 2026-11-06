import collections

from django.core.management.base import BaseCommand, CommandError
from jsondataferret.models import Record, Type

from indigo import forms, schemacheck

SCHEMAS = {
    "project": forms.PROJECT_SCHEMA,
    "organisation": forms.ORGANISATION_SCHEMA,
    "fund": forms.FUND_SCHEMA,
    "pipeline": forms.PIPELINE_SCHEMA,
    "assessment_resource": forms.ASSESSMENT_RESOURCE_SCHEMA,
    "joining_up_initiative": forms.JOINING_UP_INITIATIVE_SCHEMA,
}


class Command(BaseCommand):
    help = (
        "Check every existing record against its data standard, the way the edit form does when a record is saved "
        "unchanged, and report how many records would be refused, saved with warnings, or are clean. Nothing is "
        "changed. Use --strict to see how many were refused before the validation rules were relaxed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            action="append",
            choices=sorted(SCHEMAS),
            help="Only this type of record (can be given more than once)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat every rule as blocking, as the edit form used to",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=5,
            help="How many of the most common problems to show for each type (default 5)",
        )

    def handle(self, *args, **options):
        rules = schemacheck.STRICT_RULES if options["strict"] else None
        type_ids = options["type"] or list(SCHEMAS)
        self.stdout.write(
            "Rules: "
            + (
                "strict (everything blocks)"
                if options["strict"]
                else "relaxed (validation_rules.json)"
            )
        )
        for type_id in type_ids:
            try:
                type = Type.objects.get(public_id=type_id)
            except Type.DoesNotExist:
                raise CommandError(f"There is no {type_id} type in the database")
            self._report(type_id, type, rules, options["top"])

    def _report(self, type_id, type, rules, top):
        refused = warned = clean = 0
        problems = collections.Counter()
        for record in Record.objects.filter(type=type, cached_exists=True):
            if not record.cached_data:
                continue
            result = schemacheck.check(
                SCHEMAS[type_id],
                schemacheck.prune_blanks(record.cached_data),
                type_id,
                rules,
            )
            if result.blocking:
                refused += 1
            elif result.warnings:
                warned += 1
            else:
                clean += 1
            for kind, found in (("block", result.blocking), ("warn", result.warnings)):
                for problem in found:
                    shape = "/" + "/".join(
                        "*" if part.isdigit() else part
                        for part in problem.path.split("/")
                        if part
                    )
                    problems[(kind, problem.rule, shape)] += 1
        total = refused + warned + clean
        self.stdout.write(
            f"\n{type_id}: {total} records. "
            f"Refused: {refused}. Saved with warnings: {warned}. Clean: {clean}."
        )
        for (kind, rule, shape), count in problems.most_common(top):
            self.stdout.write(f"    {count:5}  {kind:5}  {rule:10}  {shape}")
