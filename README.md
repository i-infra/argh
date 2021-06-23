[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

Ever wanted to...

 * download/stream a video without adverts
 * download a "gif" from Twitter (etc)
 * scrape all the replies to a particular Tweet
 * save a copy of a friend's Timeline
 * pull all information available for a particular twee

etc?

Us too!

Introducing ARGH, the Augmented Roleplaying Game Helper!

The API is full of Swagger. This is almost as good as "real docs."

Check it out at https://argh.tweeter.workers.dev/!

### API Endpoints

<table><tr><td>Path</td><td>Method</td><td>Summary</td></tr><tr><td>/mm/extractors</td><td>GET</td><td>Return the list of supported multimedia extractor types</td></tr><tr><td>/mm/info</td><td>GET</td><td>" Get all info about all multimedia files at a given page</td></tr><tr><td>/mm/play</td><td>GET</td><td>Play, stream, or save a video or other multimedia file!</td></tr><tr><td>/tw/metadata</td><td>GET</td><td>Get all available metadata for a specified tweet (by URL or ID)</td></tr><tr><td>/tw/replies</td><td>GET</td><td>Get all top-level replies (optionally: all) to a particular tweet as JSON</td></tr><tr><td>/tw/timeline</td><td>GET</td><td>Return a user's timeline (100 or specified number of tweets) as JSON for easy manipulation</td></tr><tr><td>/tw/users</td><td>GET</td><td>Return metadata for one or more users</td></tr><tr><td>/version</td><td>GET</td><td>Get versions for youtube-dl, twint, and ARGH</td></tr></table>


### Setup

 * git clone https://github.com/i-infra/argh
 * sudo apt install python3-pip
 * sudo pip3 install pipenv
 * cd argh
 * pipenv install .
 * pipenv run python app.py

### Run (In Docker)

 * TODO: fill this in (TBD)

### Deploy on fly.io

 * TODO: fill this in (TBD)
