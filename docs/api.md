# API for front end site

To list projects:

    /app/api1/project
    
Note this lists both public and not public projects. 

A project can start as public and later become private, 
so it's important any consumers remove any local copies of data when they see a private flag.

This is the reason this flag is in the API! 

To get details of any public project:

    /app/api1/project/ID
    
So the process any agents who want to get the latest data should follow is:

- Get `/app/api1/project`
- For project in projects:
    - if public, get `/app/api1/project/ID`, save locally
    - If not, remove any local data you might have


