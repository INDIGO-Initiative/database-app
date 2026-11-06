"""Checking a record's data against its JSON Schema (the data standard), with some rules relaxed.

The data standard is strict, but the data people need to enter does not always fit it (a number where the standard says
text, "TBD" in a number field, a value that is nearly one of the listed options). So each problem found is sorted
into one of three kinds by the rules in validation_rules.json:

* block: the form refuses to save,
* warn: it saves, and tells the person what does not match,
* ignore: it is not mentioned.

The standard itself is not changed, and the data quality report still checks against all of it."""
import fnmatch
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

import jsonschema

BLOCK = "block"
WARN = "warn"
IGNORE = "ignore"

RULES_FILENAME = os.path.join(os.path.dirname(__file__), "validation_rules.json")

# Everything blocks: how the web forms used to check, and a way to see what the relaxed rules let through
STRICT_RULES = {"defaults": {"*": BLOCK}, "types": {}}

MAX_PROBLEMS = 50

# Text and numbers mixed up is the one kind of wrong type that can be relaxed (spreadsheet cells are a common cause)
_SCALAR_TYPES = {"string", "number", "integer", "null"}


@dataclass
class Problem:
    path: str  # a JSON pointer to the part of the data, eg /outcome_funds/0/id
    message: str
    rule: str  # the JSON Schema keyword that was broken, eg "enum"
    value: object = None  # the value that does not match, so a page can stop mentioning it once it is changed


@dataclass
class SchemaCheck:
    blocking: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@lru_cache(maxsize=None)
def load_rules():
    with open(RULES_FILENAME) as fp:
        return json.load(fp)


def _pointer(parts):
    return "".join("/" + str(p).replace("~", "~0").replace("/", "~1") for p in parts)


def _matches(pattern, segments):
    """Whether a path pattern such as /outcome_funds/*/id matches the parts of a path (list positions are "*").
    A "**" part stands for any number of parts, including none, eg **/status."""
    wanted = [p for p in pattern.split("/") if p]

    def match(wanted, segments):
        if not wanted:
            return not segments
        if wanted[0] == "**":
            return any(
                match(wanted[1:], segments[n:]) for n in range(len(segments) + 1)
            )
        return (
            bool(segments)
            and fnmatch.fnmatchcase(segments[0], wanted[0])
            and match(wanted[1:], segments[1:])
        )

    return match(wanted, segments)


def _scalar_mismatch(error):
    """For text where a number is expected, or a number where text is expected, which of the two it is: the rule name
    ("number_for_text" or "text_for_number") to look up. None for any other wrong type."""
    instance = error.instance
    if isinstance(instance, bool) or not isinstance(instance, (str, int, float)):
        return None
    expected = error.validator_value
    expected = {expected} if isinstance(expected, str) else set(expected)
    if not expected <= _SCALAR_TYPES:
        return None
    return "number_for_text" if not isinstance(instance, str) else "text_for_number"


def _mode(error, segments, rules, type_id):
    keyword = error.validator
    # The overrides for this type come first (so a type can relax a rule for all types), then the ones for every type
    overrides = rules.get("types", {}).get(type_id, {}).get(
        "overrides", []
    ) + rules.get("overrides", [])
    for override in overrides:
        if override.get("rule", "*") in (keyword, "*") and _matches(
            override["path"], segments
        ):
            return override["mode"]
    defaults = rules.get("defaults", {})
    fallback = defaults.get("*", BLOCK)
    if keyword == "type":
        kind = _scalar_mismatch(error)
        if kind is None:
            return BLOCK
        return defaults.get(kind, defaults.get("type", fallback))
    return defaults.get(keyword, fallback)


def check(schema, value, type_id, rules=None):
    """Check value against the schema. Returns a SchemaCheck of the problems that block and the ones that only warn,
    each sorted by where they are in the data."""
    rules = load_rules() if rules is None else rules
    result = SchemaCheck()
    errors = sorted(
        jsonschema.Draft7Validator(schema).iter_errors(value),
        key=lambda e: [str(p) for p in e.absolute_path],
    )
    for error in errors:
        path = list(error.absolute_path)
        segments = ["*" if isinstance(p, int) else str(p) for p in path]
        if error.validator == "required":
            # Show these against the missing field, not the group it is missing from
            found = [
                (path + [key], "This field is required", None)
                for key in error.validator_value
                if key not in error.instance
            ]
            segments_for = [
                segments + [str(key)]
                for key in error.validator_value
                if key not in error.instance
            ]
        else:
            found = [(path, error.message, error.instance)]
            segments_for = [segments]
        for (problem_path, message, value), problem_segments in zip(
            found, segments_for
        ):
            mode = _mode(error, problem_segments, rules, type_id)
            problem = Problem(_pointer(problem_path), message, error.validator, value)
            if mode == BLOCK:
                result.blocking.append(problem)
            elif mode == WARN:
                result.warnings.append(problem)
    result.blocking = result.blocking[:MAX_PROBLEMS]
    result.warnings = result.warnings[:MAX_PROBLEMS]
    return result


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def prune_blanks(value):
    """Remove blank values and the empty objects they leave behind, so a field left blank is the same as one that was
    never filled in. Blank list items are dropped; an empty list is kept (it means "no rows").

    This is the same as prune() in frontend/src/utils.js, which the edit form runs before it saves."""
    if isinstance(value, list):
        pruned = [prune_blanks(item) for item in value]
        return [
            item
            for item in pruned
            if not _is_blank(item) and not (isinstance(item, dict) and not item)
        ]
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            pruned = prune_blanks(item)
            if _is_blank(pruned) or (isinstance(pruned, dict) and not pruned):
                continue
            out[key] = pruned
        return out
    return value
