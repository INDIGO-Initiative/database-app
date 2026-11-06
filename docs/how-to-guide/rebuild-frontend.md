# Rebuild the frontend (RJSF edit forms)

The project edit form is a React JSON Schema Form (RJSF). The source is in `frontend/`. The compiled script and stylesheet
are checked in to git in `indigo/static/rjsf/`, so deploying does not need Node.

You only need to do this if you change something in `frontend/src/`, or the section groups in `indigo/section_groups.json`.

`indigo/section_groups.json` says which parts of a project go in which tab of the edit form. The record pages (public and admin) read the same file to make their sections, so the two always match. The edit form has the file built into the bundle, so rebuild after changing it.
(Changes to the data standard schema do not need a rebuild; the schema is read by Django when the page loads.)

Use the Node version in `frontend/.nvmrc` (`nvm use`).

```
cd frontend
npm install
npm test
npm run build
```

Commit the changed files in `indigo/static/rjsf/` along with your source changes.

Without a rebuild, nothing in `frontend/` has any effect.

## How it fits together

* `RJSFSchemaField` and `RJSFWidget` in `indigo/forms.py` put the schema, the current data and a hidden input on the page.
* `frontend/src/main.jsx` finds the `.rjsf-holder` element, shows the tabbed form and keeps the hidden input up to date.
* On save, Django checks the whole record against the schema and sends the edit to moderation.
* The organisation picker uses `admin/organisation_search_json`.
