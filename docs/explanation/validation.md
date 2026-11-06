# How data is checked against the data standard

The data standard is a JSON Schema for each type of record (`data-standard/` and the other data standard folders, compiled
into `indigo/jsonschema/cached_information/`). It says which fields exist, their types, the options in lists, patterns
and so on. The standard is strict, but the data people need to enter does not always fit it: a number where the standard
says text, "TBD" in a number field, a value that is nearly one of the listed options. The standard cannot be changed
every time that happens, so the app decides how seriously to take each kind of mismatch.

## Where checks happen

| Where | What it does with a mismatch |
|---|---|
| The web edit forms | Applies the rules below: a mismatch can block the save, or let it save with a warning |
| Spreadsheet uploads | Never blocks. The values are read from the cells and saved. |
| When an edit is approved | The `jsondataferret` library checks the whole record against the full standard and stores the list of problems on the record (`cached_jsonschema_validation_errors`). Nothing reads it yet. |
| The Data Quality Report, and the warning on the second step of a project or pipeline import | Check against the full standard and only report |

Only the first of these ever blocks anything. Relaxing it changes no stored data: the rules are only applied when someone
saves, and they never rewrite values.

## The rules for the web forms: `indigo/validation_rules.json`

Each kind of mismatch (named after the JSON Schema keyword that was broken) is one of:

* `block`: the form refuses to save, and shows the problem against the field.
* `warn`: the form saves, and the page after saving lists what does not match the standard.
* `ignore`: nothing is said.

The file's `defaults` set this for every type of record. The ones that matter most:

* `number_for_text`: a number where the standard says text. This is usually a spreadsheet cell. Ignored, because it is
  harmless.
* `text_for_number`: text in a number field, such as "TBD". A warning.
* `enum`: a value that is not one of the listed options. A warning.
* `pattern`, `format`, `minLength`, `maxLength`, `minimum`, `maximum`, `minItems`, `maxItems`: warnings.
* `required` and anything not listed (`*`): block.
* A `status` (PUBLIC, PRIVATE or DISPUTED) that is not one of its options always blocks, because status decides what is
  shown publicly and a mistyped one would quietly hide or expose data. This is an override for every type in the file
  (`"path": "**/status"`).

The wrong *shape* of data always blocks, for example a single value where a group of fields is expected, or a list where
a single value is expected. The form could not make sense of that.

### Changing a rule for one type or field

Add an override to `types` in the same file (or to the top-level `overrides`, which apply to every type). The first
override that matches wins, and a type's own overrides are looked at before the ones for every type. `path` is the
position in the data, where `*` stands for any list position (or any one name) and `**` for any number of parts, and
`rule` is the keyword (leave it out for every keyword):

```json
"types": {
  "project": {
    "overrides": [
      {"path": "/outcome_payment_plans/*/period/end_date/value", "rule": "pattern", "mode": "block"},
      {"path": "/investments/*/investment_type/value", "rule": "enum", "mode": "ignore"}
    ]
  }
}
```

No rebuild is needed, but restart the app so it reads the file again.

## What the person editing sees

* **When the form opens**, any value in the record that does not match the standard but is allowed is marked in amber
  under its field, with the reason, and each tab with some has an amber count. Values the server refuses when saving are
  still shown in red.
* **A warning is about the value as it was loaded.** Once the value is changed the warning goes, even if the new value
  is also odd. After saving, the page says how many values do not match, so nothing is silent.
* **Lists of options** are a dropdown with an extra "Other (type your own)..." choice, which shows a text box. A value
  that is not in the list is shown in that text box, so it is visible and kept instead of vanishing from a dropdown that
  cannot show it. A status is always a plain dropdown.

## What the standard itself still does

Nothing is taken out of the standard. The Data Quality Report still checks everything against it, so values that were
allowed to save with a warning stay visible there, and can be tidied later.

## Checking what the rules do to existing records

```
django-admin checkrecordsagainstschema            # with the rules in validation_rules.json
django-admin checkrecordsagainstschema --strict   # as the forms behaved before the rules were relaxed
```

Both read every record and report, for each type, how many would be refused if saved unchanged, how many would save with
warnings, and how many are clean, plus the most common problems. `--type` limits it to one type, and `--top` changes how
many problems are listed. Nothing is changed. The check removes blank values first, as the edit form does before saving.
Run it on a copy of production data to see the effect of a change to the rules before it is deployed.
