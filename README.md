# MoviesBot

MoviesBot is a reddit bot that looks for IMDB links in reddit posts and replies with links to stream, rent, and purchase the movies. The IMDB links are crossrefrenced with [Can I Stream.it](canistream.it) to populate the information.

Comments include a table with all information that was found for the movies listed.

![moviesbot screenshot](http://i.imgur.com/V0YtY6x.png)

This reddit bot runs on Google App Engine, and once configured, can be uploaded to run in GAE and run with the resources provided with the free quotas

## Quickstart for deploying in Google App Engine

1) Go to the [Google Developers Console](https://console.developers.google.com/project) and click on Create Project

2) Fill out the form, and take note of your Project ID

3) clone this repo and save to the name of the project ID
> git clone https://github.com/stevenviola/moviesbot.git <project id>

4) Copy the config template and fill out with reddit account info
> cp config-template.yml config.yaml

5) Deploy to Google App Engine
> google_appengine/appcfg.py update <project id>/

## Configuration File Explination

### Reddit
>    user: username

The username that you use to sign into Reddit with

>    password: supersecretpassword

The password that you use to sign into Reddit with

>    client_id: clientid

>    client_secret: clientsecret

For the client info, in the [apps section of reddit prefrences](https://www.reddit.com/prefs/apps/), you need to create an app, and get this info from the app page

### Imgur

Imgur is currently not used, and this is a placeholder for future implemention

### Rotten Tomatoes

We currently do not need to authenticate to get the Rotten Tomatoes information. This section is a placeholder if there is information we will need from Rotten Tomatoes that requires authentication

## TODO

- Utilize Google App Engine Task Queues for parallel processing when retriving post information
- Create frontend to view stats on most mentioned movies on Reddit

## Further Reading

The [moviesbot FAQ](https://www.reddit.com/r/moviesbot/wiki/faq) details how to interact with this bot on Reddit

## Credits

All code in this repository was developed by Steven Viola

Information id provided by [the OMDb API](http://www.omdbapi.com/) and [Can I Stream.It](http://www.canistream.it/)