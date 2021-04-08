# Upgrade Python Libraries

As this is an app, dependencies are pinned in requirements files (in the root of the repository)p

https://pypi.org/project/pip-tools/ are used and included in the dev requirements.

Upgrade with the normal pip-tools process.

    pip-compile --upgrade
    pip-compile --upgrade requirements_dev.in

Note: After upgrading [you may need to rebuild caches checked into git](rebuild-caches-checked-in-to-git.md).

