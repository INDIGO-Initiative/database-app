# Dev notes

## On Python upgrades

If upgrading the versions of python libs, you must run the command

    python manage.py updatestaticcache

and check the resulting changes into git.

This is because this command caches information in git, and the format of the cache may change when the libraries are 
upgraded. To make sure the cache is in the right format for the version of the libraries currently installed, this 
command should be run.
