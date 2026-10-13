"""Turns a record's data into the sections shown on a record page (public and admin), the way the edit form groups it.

A record page has a sidebar of sections. Each section has blocks: a table of single fields (with a heading when a group
of related fields is long enough to need one), or a repeating list, shown as one card for each item.

The grouping follows the edit form: indigo/section_groups.json says which top-level parts of a project go in which
section; the other types get a "General" section and a section for each repeating list."""
import functools
import json
import os

import jsonpointer
from django.conf import settings
from django.utils.text import slugify

from indigo.utils import tidy_field_title

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, "section_groups.json")) as fp:
    SECTION_GROUPS = json.load(fp)

# Titles of these start with the name of the type ("Fund - Dates - ..."), which says nothing on a page about a fund
TYPE_TITLE_PREFIXES = {
    "fund": "Fund",
    "assessment_resource": "Assessment Resource",
    "joining_up_initiative": "Joining Up Initiative",
}


@functools.lru_cache(maxsize=None)
def _group_titles(type_public_id):
    """The title of each top-level part of the data, from the schema (eg "dates": "Dates")."""
    path = os.path.join(
        BASE_DIR,
        "jsonschema",
        "cached_information",
        f"{type_public_id}.json.compiled_jsonschema.json",
    )
    try:
        with open(path) as fp:
            schema = json.load(fp)
    except OSError:
        return {}
    return {
        key: value.get("title")
        for key, value in schema.get("properties", {}).items()
        if isinstance(value, dict) and value.get("title")
    }


def _pretty_key(key):
    return key.replace("_", " ").strip().capitalize()


def _without_type_prefix(title, type_public_id):
    prefix = TYPE_TITLE_PREFIXES.get(type_public_id)
    if prefix and title.startswith(prefix + " - "):
        return title[len(prefix) + 3 :]
    return title


def _label(title, type_public_id, group_title=None):
    """A field's title without the parts the page already makes clear."""
    title = _without_type_prefix(title, type_public_id)
    if group_title and title.startswith(group_title + " - "):
        title = title[len(group_title) + 3 :]
    return tidy_field_title(title)


def _group_heading(key, schema_titles, rows, type_public_id):
    """The heading of a group of fields: its title in the schema, or failing that the start that all the fields' titles
    share ("Type of instrument and project - Outcomes Fund"...), or failing that its key made readable."""
    if schema_titles.get(key):
        return schema_titles[key]
    firsts = {
        _without_type_prefix(title, type_public_id).split(" - ")[0] for title, _ in rows
    }
    if len(firsts) == 1 and all(" - " in title for title, _ in rows):
        return firsts.pop()
    return _pretty_key(key)


def _value(data, pointer):
    """The value at the pointer, or None if there is none (or it is empty)."""
    try:
        value = jsonpointer.resolve_pointer(data, pointer)
    except jsonpointer.JsonPointerException:
        return None
    return value or None


def _collect(type_public_id, data):
    """The data's fields grouped by top-level key, in the order the type lists them, leaving out anything empty.

    Returns {top key: {"kind": "fields", "rows": [(raw title, value)]} or
                      {"kind": "list", "title", "items": [{"title", "rows": [(raw title, value)]}]}}"""
    config = settings.JSONDATAFERRET_TYPE_INFORMATION.get(type_public_id, {}).get(
        "fields", []
    )
    collected = {}
    for field in config:
        top_key = field["key"].split("/")[1]
        if field.get("type") == "list":
            try:
                values = jsonpointer.resolve_pointer(data, field["key"])
            except jsonpointer.JsonPointerException:
                continue
            if not isinstance(values, list):
                continue
            list_title = _without_type_prefix(field["title"], type_public_id)
            items = []
            for n, item in enumerate(values, start=1):
                rows = [
                    (item_field["title"], value)
                    for item_field in field["fields"]
                    if (value := _value(item, item_field["key"])) is not None
                ]
                if rows:
                    items.append({"title": f"{list_title} {n}", "rows": rows})
            if items:
                collected[top_key] = {
                    "kind": "list",
                    "title": list_title,
                    "items": items,
                }
        else:
            value = _value(data, field["key"])
            if value is not None:
                collected.setdefault(top_key, {"kind": "fields", "rows": []})[
                    "rows"
                ].append((field["title"], value))
    return collected


def _blocks(type_public_id, keys, collected):
    """The blocks of a section made of these top-level keys."""
    titles = _group_titles(type_public_id)
    blocks = []
    singles = (
        []
    )  # fields that are alone in their group share one table, with no heading

    def flush_singles():
        if singles:
            blocks.append({"kind": "fields", "title": None, "rows": list(singles)})
            singles.clear()

    for key in keys:
        group = collected[key]
        if group["kind"] == "list":
            flush_singles()
            blocks.append(
                {
                    "kind": "list",
                    "title": group["title"],
                    "items": [
                        {
                            "title": item["title"],
                            "rows": [
                                {"title": _label(title, type_public_id), "value": value}
                                for title, value in item["rows"]
                            ],
                        }
                        for item in group["items"]
                    ],
                }
            )
        elif len(group["rows"]) == 1:
            title, value = group["rows"][0]
            singles.append({"title": _label(title, type_public_id), "value": value})
        else:
            flush_singles()
            group_title = _group_heading(key, titles, group["rows"], type_public_id)
            blocks.append(
                {
                    "kind": "fields",
                    "title": group_title,
                    "rows": [
                        {
                            "title": _label(title, type_public_id, group_title),
                            "value": value,
                        }
                        for title, value in group["rows"]
                    ],
                }
            )
    flush_singles()
    return blocks


def _count(blocks):
    return sum(
        len(block["rows"]) if block["kind"] == "fields" else len(block["items"])
        for block in blocks
    )


def build_record_sections(type_public_id, data):
    """The sections of a record page: [{"id", "title", "count", "blocks"}], leaving out sections with nothing in."""
    collected = _collect(type_public_id, data or {})
    layout = []  # (section title, top-level keys)
    groups = SECTION_GROUPS.get(type_public_id)
    if groups:
        used = set()
        for title, keys in groups:
            present = [k for k in keys if k in collected]
            used.update(present)
            layout.append((title, present))
        layout.append(("Other", [k for k in collected if k not in used]))
    else:
        layout.append(
            ("General", [k for k, g in collected.items() if g["kind"] == "fields"])
        )
        layout.extend(
            (g["title"], [k]) for k, g in collected.items() if g["kind"] == "list"
        )

    sections = []
    seen_ids = set()
    for title, keys in layout:
        if not keys:
            continue
        blocks = _blocks(type_public_id, keys, collected)
        section_id = base_id = "section-" + (slugify(title) or "section")
        n = 1
        while section_id in seen_ids:
            n += 1
            section_id = f"{base_id}-{n}"
        seen_ids.add(section_id)
        sections.append(
            {
                "id": section_id,
                "title": title,
                "count": _count(blocks),
                "blocks": blocks,
            }
        )
    return sections
