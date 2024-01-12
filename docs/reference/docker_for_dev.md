# Development and the docker environment

Docker compose can be used as a local development environment.

To run:

```
docker compose -f docker-compose.dev.yml up
```

The app will be at http://localhost:8000/app/

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

## Importing a database dump from Heroku

**Be very aware you will have data here that must be kept PRIVATE.**

### Clear out old database

If you already have a database, you need to clear out the old one.

Stop the usual Docker Compose Up command and instead run this command that only runs the database:

```commandline
docker compose -f docker-compose.dev.yml up postgres
```

Run in console:

```
docker compose -f docker-compose.dev.yml run postgres  su -c 'PGPASSWORD=1234 psql   -U postgres -h postgres postgres'
```

Run in Shell:

```
DROP DATABASE app;
CREATE DATABASE app WITH OWNER postgres ENCODING 'UTF8'  LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8'  TEMPLATE=template0 ;
\q
```

You can now switch back to the normal Docker Compose Up command before moving to the import.

### Import

Put the file in the project directory so it is accessible to docker then run:

```
docker compose -f docker-compose.dev.yml run postgres  su -c 'PGPASSWORD=1234 pg_restore -d app -U postgres -h postgres   /app/import-20XX-YY-ZZ.sql'
```

## Lint

```
docker compose -f docker-compose.dev.yml run indigo-database-app-dev black djangoproject/ indigo/ manage.py
docker compose -f docker-compose.dev.yml run indigo-database-app-dev flake8 djangoproject/ indigo/ manage.py
```

## Restarting app server and worker without also restarting database and message queue server

If you change code, you may need to restart the app or worker. This will do so quickly:

```
docker compose -f docker-compose.dev.yml  restart indigo-database-app-dev && docker compose -f docker-compose.dev.yml  restart indigo-database-worker-dev
```

## Running tests

To run the tests with docker compose locally:

```bash
docker compose  -f docker-compose.test.yml  -p indigo-database-test up
```

As before, you'll need to rebuild the docker environment if you add, remove, or upgrade the dependencies:

```bash
docker compose  -f docker-compose.test.yml -p indigo-database-test down
docker compose  -f docker-compose.test.yml -p indigo-database-test build --no-cache
docker compose  -f docker-compose.test.yml -p indigo-database-test up
```

## Running commands

Make sure environment is running (see up command above) then:

```
docker compose -f docker-compose.dev.yml run indigo-database-app-dev python manage.py migrate
```

## Updating the Dockerfile

If you make changes to either `Dockerfile` or `docker-compose.dev.yml` you'll need to rebuild it locally to test it:

```
docker compose -f docker-compose.dev.yml down # (if running)
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up # (to restart)
```

## Python Packages Upgrade

This will upgrade all packages:

```
docker compose -f docker-compose.dev.yml run indigo-database-app-dev pip-compile --upgrade
docker compose -f docker-compose.dev.yml run indigo-database-app-dev pip-compile --upgrade requirements_dev.in
docker compose -f docker-compose.dev.yml down # (if running)
docker compose -f docker-compose.dev.yml build --no-cache
```

If you temporarily want to use an unreleased version of a library, edit `requirements.in` to something like:

```
git+https://github.com/OpenDataServices/json-data-ferret.git@2022-10-26#egg=jsondataferret
```

then run the above. Don't put `-e` at the start - that doesn't work for some reason.

