# Heroku for production/testing

This app is designed to run on Heroku

## Set up

Set up an app in Europe.

Add a Heroku Postgres Database - make sure it saves it's credentials as `DATABASE_URL`.

Add the Config Vars `ON_HEROKU` and set it's value to `1`.

Add the Config Vars `SECRET_KEY` and set it's value to something random and secret.

Add the Config Vars `SENTRY_DSN` and set it's value to whatever Sentry tells you.

Deploy by normal Heroku methods. 

Use the `Run console` option and the normal Django `createsuperuser` command to create your first admin user.

In the Django admin console, go to the `Jsondataferret` section, `Types` option. Add the following 3 records:

* public id: project, title: Project
* public id: organisation, title: Organisation
* public id: fund, title: Fund

The app is now ready to use

## Deploying

Simply deploy by normal Heroku methods. Nothing special needs to be done.
