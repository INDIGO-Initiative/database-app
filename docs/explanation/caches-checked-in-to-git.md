# Caches checked into Git

Some files are cached in Git. These can be found in:

* https://github.com/INDIGO-Initiative/database-app/tree/live/indigo/jsonschema/cached_information
* https://github.com/INDIGO-Initiative/database-app/tree/live/indigo/spreadsheetform_guides/cached_information

This is because the app needs to pull out some information from various files to work with. 

We were doing this at app start-up time, however it started to take a very long time (20 seconds or more). This was annoying to developers, but also a problem for Heroku. If a Heroku app takes too long to start Heroku assumes it has crashed.

As an alternative, certain information is now cached in git. This keeps app start-up time very fast.

Every time certain things change, the cache command should be rerun and the results checked into git in the same commit or pull request.

See [the how-to guide for more](../how-to-guide/rebuild-caches-checked-in-to-git.md)

