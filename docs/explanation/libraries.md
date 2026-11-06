# Libraries

A list of the key libraries we use, and links to documentation:

* Django https://www.djangoproject.com/ 
  Web Framework
* JSON Data Ferret https://json-data-ferret.readthedocs.io/en/latest/ 
  Manages JSON blobs of data in database, with history and moderation.
  We only use it as a library. Its own web pages (at `/jsondataferret/`) are not switched on: the app's admin pages do the same jobs with our permissions and validation, and old links to those pages redirect to the admin home page.
* Spreadsheet forms https://spreadsheet-forms.readthedocs.io/en/latest/ 
  Converts Excel Spreadsheets to JSON and vice versa
* React JSON Schema Form (RJSF) https://rjsf-team.github.io/react-jsonschema-form/
  The web forms for editing records. The source is in `frontend/`, and the compiled bundle is checked in to
  `indigo/static/rjsf/`, so deploying does not need Node. See [Rebuild the frontend](../how-to-guide/rebuild-frontend.md).
* Bootstrap 4 https://getbootstrap.com/docs/4.4/ and Font Awesome 6 https://fontawesome.com/
  Page styling and icons, loaded from a CDN. Our own styles are in `indigo/static/css/main.css`.
* django-filter https://django-filter.readthedocs.io/
  The date filters on the History page.

For how the pages are put together, see [How the admin and public pages are built](admin-and-public-pages.md).
