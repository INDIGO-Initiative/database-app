# Indigo App

## CURRENT USE

Run database migrations

Create a superuser via normal django command line tool

Log into /admin

Add some Types:

* public id: project, title: Project
* public id: organisation, title: Organisation

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
