# Libraries

A list of the key libraries we use, and links to documentation:

* Django https://www.djangoproject.com/ 
  Web Framework
* JSON Data Ferret https://json-data-ferret.readthedocs.io/en/latest/ 
  Manages JSON blobs of data in database, with history and moderation.
  We only use it as a library. Its own web pages (at `/jsondataferret/`) are not switched on: the app's admin pages do the same jobs with our permissions and validation, and old links to those pages redirect to the admin home page.
* Spreadsheet forms https://spreadsheet-forms.readthedocs.io/en/latest/ 
  Converts Excel Spreadsheets to JSON and vice versa
