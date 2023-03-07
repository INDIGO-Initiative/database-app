# Heroku for production/testing

This app is designed to run on Heroku.

## Set up

Set up an app in Europe.

Add a Heroku Postgres Database - make sure it saves it's credentials as `DATABASE_URL`. (The live dataset has more than 10,000 rows so the free database is probably not suitable.)

Add a CloudAMQP service - make sure it saves it's credentials as `CLOUDAMQP`. (The free service is probably fine)

Add the Config Var `ON_HEROKU` and set it's value to `1`.

Add the Config Var `SECRET_KEY` and set it's value to something random and secret.

Add the Config Var `API_SANDBOX_DATA_PASSWORD` and set it's value to something random and secret.

Add the Config Var `SENTRY_DSN` and set it's value to whatever Sentry tells you.

If it's a test server, you can also add the the Config Var `APP_TITLE` and set a test title like `INDIGO Test Server`.
This will help users tell the difference between test and live servers. Don't set this var on the live server.

S3 storage is required for Heroku. See [the S3 page](s3.md) for details of setting up the bucket
and environmental variables to set.

If you have a database to import, please do so at this stage (ie before deploying).

Deploy by the normal Heroku method of pushing via git. You must use this method and not the API, Web UI, etc, because this app uses Git Submodules and [they only work via a git push](https://devcenter.heroku.com/articles/git-submodules).

Set up the Cron / Scheduler, using the notes below.

If you imported a database, at this stage you are done. If not, there are some final steps to do to set up the database.

Use the `Run console` option and the normal Django `createsuperuser` command to create your first admin user.

In the Django admin console, go to the `Jsondataferret` section, `Types` option. Add the following 4 records:

* public id: project, title: Project
* public id: organisation, title: Organisation
* public id: fund, title: Fund
* public id: assessment_resource, title: Assessment Resource
* public id: pipeline, title: Pipeline
* public id: joining_up_initiative, title: Joining Up Initiative

The app is now ready to use!

## Deploying

Deploy by the normal Heroku method of pushing via git. You must use this method and not the API, Web UI, etc, because this app uses Git Submodules and [they only work via a git push](https://devcenter.heroku.com/articles/git-submodules).

If the public spreadsheets or rules about which data is available to the public have changed, you will need to update Caches.

Run one after the other:

    python manage.py updatedata
    python manage.py updateprojectfiles
    python manage.py updatefundfiles
    python manage.py updatepipelinefiles
    python manage.py updateorganisationfiles

Then watch the worker logs and wait till all tasks are done. Then run:

    python manage.py updatearchivefiles


## Cron / Scheduler

The commands:

    python manage.py updateprojectfiles
    python manage.py updateorganisationfile
    python manage.py updatefundfiles
    python manage.py updatepipelinefiles
    python manage.py updatearchivefiles

Should be run once per day.

They should be run in the order above with a gap in-between each one; say 30 mins.

