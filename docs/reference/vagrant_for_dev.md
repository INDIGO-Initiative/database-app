# Vagrant for Development

A vagrant box exists to help developers.

Simply run `vagrant up`.

After `vagrant ssh`, run `cd /vagrant` and `source .ve/bin/activate`.

## Run Web Server

    python manage.py runserver 0:8000

Go to `http://localhost:8000`

## Run Worker

    celery -A indigo worker -l info

## Set up app for first time

If you have a database to import, you can do that instead (see below) and skip this.

Run normal Django database migrations.

Create a superuser via normal django command line tool.

Run the webserver.

Log into `/admin`.

Add some `Types` records in the `Jsondataferret` section :

* public id: `project`, title: `Project`
* public id: `organisation`, title: `Organisation`
* public id: `fund`, title: `Fund`
* public id: `pipeline`, title: `Pipeline`
* public id: `assessment_resource`, title: `Assessment Resource`

## Python Packages Upgrade

    pip-compile --upgrade
    pip-compile --upgrade requirements_dev.in
    
## Tests

The Vagrant box sets up a second database, so running tests won't alter your current working data.

Run:

    JSONDATAFERRET_DATABASE_NAME=test JSONDATAFERRET_DATABASE_USER=test JSONDATAFERRET_DATABASE_PASSWORD=test CLOUDAMQP_URL=memory:// python manage.py test

## Code Quality

Clean up code before you commit:

    isort --recursive djangoproject/ indigo/
    black djangoproject/ indigo/
    flake8 djangoproject/ indigo/


## Checking live data

If you have a database you want to restore into your vagrant box, put the file in the folder so it appears in your vagrant box then:

    sudo su postgres
    psql -c "DROP DATABASE app"
    psql -c "CREATE DATABASE app WITH OWNER app ENCODING 'UTF8'  LC_COLLATE='en_GB.UTF-8' LC_CTYPE='en_GB.UTF-8'  TEMPLATE=template0 "
    exit
    pg_restore -d app -U app -h localhost    /vagrant/indigo-backup-01.sql

**Be very aware you will have data here that must be kept PRIVATE.**
