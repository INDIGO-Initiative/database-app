# Heroku for production/testing

This app is designed to run on Heroku

## Set up

Set up an app in Europe.

Add a Heroku Postgres Database - make sure it saves it's credentials as `DATABASE_URL`.

Add a CloudAMQP service - make sure it saves it's credentials as `CLOUDAMQP`.

Add the Config Var `ON_HEROKU` and set it's value to `1`.

Add the Config Var `SECRET_KEY` and set it's value to something random and secret.

Add the Config Var `SENTRY_DSN` and set it's value to whatever Sentry tells you.

If it's a test server, you can also add the the Config Var `APP_TITLE` and set a test title like `INDIGO Test Server`. 
This will help users tell the diference between test and live servers. Don't set this var on the live server.

S3 storage is required for Heroku. See [the S3 page](s3.md) for details of setting up the bucket 
and environmental variables to set.

Deploy by normal Heroku methods. 

Use the `Run console` option and the normal Django `createsuperuser` command to create your first admin user.

In the Django admin console, go to the `Jsondataferret` section, `Types` option. Add the following 3 records:

* public id: project, title: Project
* public id: organisation, title: Organisation
* public id: fund, title: Fund

The app is now ready to use!

## Deploying

Simply deploy by normal Heroku methods. Nothing special needs to be done.

If the public spreadsheets have changed, you will want to run commands to regenerate all spreadsheets in storage.

Run:

    python manage.py updateprojectfiles
    python manage.py updatefundfiles
    python manage.py updateorganisationfiles

Then watch the worker logs and wait till all tasks are done. Then run:

    python manage.py updatearchivefiles


## Cron / Scheduler

The command:

    python manage.py updatearchivefiles

Should be run regularly.

