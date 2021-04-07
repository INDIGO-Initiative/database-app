# Rebuild caches checked into Git

Some files are cached in Git. [See this for an explanation](../explanation/caches-checked-in-to-git.md).

The cache needs to be rebuilt and checked into git when the following things happen:

* The spreadsheet form guides change, or a new one is added ([See Guide](alter-or-create-a-new-spreadsheet-form.md))
* The schemas change https://github.com/INDIGO-Initiative/database-app (submodule in data-standard)
* The version of the Spreadsheet forms library changes (because upgrades to this library may produce cache files in a different format)

To rebuild them, simply run

    python manage.py updatestaticcache

Check the changes into git in the same commit or pull request as the thing that changed it.
