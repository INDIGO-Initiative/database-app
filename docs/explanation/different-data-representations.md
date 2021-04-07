# Different Data Representations

There are actually several different representations of data that may exist in the system at various points.

## The single source of truth schema

The main schema is defined at https://github.com/INDIGO-Initiative/indigo-data-standard/tree/main/schema 

This is the schema the database saves data as in as the Single Source Of Truth; the main and only store. (Other data is cached in the database; we will come back to that.)

A history of all changes to the data is also stored in this schema. 

Moderation features are provided over this data.

The storage of the data, history and moderation features are all provided by [the JSON Data Ferret library](libraries.md).

## Public and Sandbox API Data

A process must be followed to get a slightly different schema to release to the public via the API. This process:

* Removes some data depending on status fields
* Always removes some data
* Add some extra data to make the spreadsheet more useful (For instance in the single source of truth schema, only organisation ID's are stored. We add organisation names to make the data more readable.)
* Changes some deprecated values to new values, so data is consistent. (See `map_project_values` in `indigo/updatedata.py`)

This is done in `indigo/updatedata.py` by the functions:

* `update_project`
* `update_organisation`
* `update_fund`
* `update_assessment_resource`

These functions are triggered any time the single source of truth data changes by a hook in `indigo/jsondataferret.py`.

They can also be triggered manually by running `python manage.py updatedata`. (This may be needed if one of the rules on how to prepare data changes, or the schema of public and sandbox API data changes.) 

In each case the results are cached in the database on the `data_public` column/variable of the following models:

* `Project`
* `Organisation`
* `Fund`
* `AssessmentResource`

(In fact, all the data in these 4 tables/models is a cached version of data elsewhere.)

If there is sandbox data, it is also cached in `data_sandboxes` column/variable.

## When editing Public Spreadsheets

A process must be followed to get a slightly different schema to put into a public spreadsheet, for the same reasons as above.

In `indigo/spreadsheetforms.py`, this is done by the 4 functions:

* `convert_project_data_to_spreadsheetforms_data`
* `convert_organisation_data_to_spreadsheetforms_data`
* `convert_fund_data_to_spreadsheetforms_data`
* `convert_assessment_resource_data_to_spreadsheetforms_data`

## When editing Admin Spreadsheets

Like the above section, a process must be followed to get a slightly different schema to put into an admin spreadsheet. 

In `indigo/spreadsheetforms.py`, this is done by the same 4 functions (with different parameters):

* `convert_project_data_to_spreadsheetforms_data`
* `convert_organisation_data_to_spreadsheetforms_data`
* `convert_fund_data_to_spreadsheetforms_data`
* `convert_assessment_resource_data_to_spreadsheetforms_data`

However, the process also needs to happen in reverse. When an admin spreadsheet is imported, and JSON data extracted, some small changes need to be made to get the single source of truth schema that should be saved to the database.

In `indigo/spreadsheetforms.py`, this is done by the 4 functions:

* `extract_edits_from_project_spreadsheet`
* `extract_edits_from_organisation_spreadsheet`
* `extract_edits_from_fund_spreadsheet`
* `extract_edits_from_assessment_resource_spreadsheet`

## Data Flows between schemas

So we can essentially think of this as:

* Single source of truth data
* Single source of truth data  => Public and Sandbox API Data ( A one way conversion )
* Single source of truth data  => Public Spreadsheet Data  ( A one way conversion )
* Single source of truth data  <=> Private Spreadsheet Data  ( A two way conversion )

## The differences between the API data and the data for the Spreadsheets

There is no conceptual reason why the "Public API Data" and the "Spreadsheet Data" should be related at all.

In practice, it turns out we want to do some of the same things to both sets of data. 

For that reason, the `convert_*_data_to_spreadsheetforms_data` functions may work off the cached `data_public` column/variable. Eg:

* Single source of truth data  => Public API Data => Public Spreadsheet Data ( A one way conversion )

But in the future, if the needs of these 2 purposes diverge, this may change.

## Where can I see these data schemas?

Single Source of Truth data: https://github.com/INDIGO-Initiative/indigo-data-standard/tree/main/schema 

The API format: There is currently no good documentation that exactly explains this schema. As this is available publically, there should be.

The spreadsheet format: There is currently no good documentation that exactly explains this schema. However, as this is only used internally and a user of the system should never see it this is less important.
