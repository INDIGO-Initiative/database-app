# API for front end site

## Server name

The live server is: https://golab-indigo-data-store.herokuapp.com

If you are working of a test server for test data, you may be working of a different server. In that case change the domain in the URL's on this page.

## Projects as JSON

To list projects:

    https://golab-indigo-data-store.herokuapp.com/app/api1/project
    
Note this lists both public and not public projects. 

A project can start as public and later become private, 
so it's important any consumers remove any local copies of data when they see a private flag.

This is the reason this flag is in the API! 

To get details of any public project:

    https://golab-indigo-data-store.herokuapp.com/app/api1/project/ID
    
So the process any agents who want to get the latest data should follow is:

- Get `https://golab-indigo-data-store.herokuapp.com/app/api1/project`
- For project in projects:
    - if public, get `https://golab-indigo-data-store.herokuapp.com/app/api1/project/ID`, save locally
    - If not public, remove any local data you might have

## Organisations as JSON

This works the same as projects, but with different end points:

    https://golab-indigo-data-store.herokuapp.com/app/api1/organisation
    https://golab-indigo-data-store.herokuapp.com/app/api1/organisation/ID

## Assessment Resources as JSON

This works the same as projects, but with different end points:

    https://golab-indigo-data-store.herokuapp.com/app/api1/assessment_resource
    https://golab-indigo-data-store.herokuapp.com/app/api1/assessment_resource/ID

## Funds as JSON

This works the same as projects, but with different end points:

    https://golab-indigo-data-store.herokuapp.com/app/api1/fund
    https://golab-indigo-data-store.herokuapp.com/app/api1/fund/ID

## Sandbox access while getting JSON

Sandboxes contain projects, funds, etc as usual, but there may be special data that is only available in a sandbox.

To see this data, you must pass a password to the API calls when getting JSON.

Pass the password as a GET parameter called `sandbox_data_password` eg: 

    https://golab-indigo-data-store.herokuapp.com/app/api1/project/ID?sandbox_data_password=PASSWORD

## Other Data Formats

You can also download:

* Some CSV's
* Some Zip files with CSV's
* Some Zip files with Excel files

To find these: 

* See the public site at: https://golab.bsg.ox.ac.uk/knowledge-bank/indigo/download-indigo-data/
* Browse the app public site at https://golab-indigo-data-store.herokuapp.com/app/
* Browse the app public site at https://golab-indigo-data-store.herokuapp.com/app/project
* Browse the app public site at https://golab-indigo-data-store.herokuapp.com/app/organisation

