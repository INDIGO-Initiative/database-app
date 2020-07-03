# Indigo App

## CURRENT USE

Run database migrations

Create a superuser via normal django command line tool

Log into /admin

Add some Types:

* public id: project, title: Project
* public id: organisation, title: Organisation
* public id: fund, title: Fund

Go to /app - work with data!

Go to /jsondataferret - backend view of data management

## Run 

    python manage.py runserver 0:8000


## Python Packages Upgrade

    
    pip-compile --upgrade
    pip-compile --upgrade requirements_dev.in
    
    
## Dev


Run tests  (with Vagrant DB credentials):



    JSONDATAFERRET_DATABASE_NAME=test JSONDATAFERRET_DATABASE_USER=test JSONDATAFERRET_DATABASE_PASSWORD=test python manage.py test

Clean up code before commit:



    isort --recursive djangoproject/ indigo/
    black djangoproject/ indigo/
    flake8 djangoproject/ indigo/

## API for front end site

To list:

    /app/api1/project
    
Note this lists public and not public projects. 
A project can start as public and later become private, so it's important any consumers remove any local copies of data when they see a private flag.
This is the reason this flag is in the API! 

To get details of any public project:

    /app/api1/project/ID
    
So process:

- Get /app/api1/project
- For project in projects:
    - if public, get /app/api1/project/ID, save locally
    - If not, remove any local data you might have


