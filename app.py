import calendar
import functools
import logging
import os
import sys
import traceback
import urllib.request

import arrow
import youtube_dl
from flask import Flask, Response, current_app, redirect, request
from youtube_dl.version import __version__ as youtube_dl_version

import utwee
import utwint.get

service = os.environ.get("K_SERVICE", "Unknown service")
revision = os.environ.get("K_REVISION", "Unknown revision")


from random import choice, random
from time import sleep, time

from decorator import decorator
from flask_restx import Api, Resource, fields, reqparse

argh_version = "0.9"
app = Flask("__main__")
app.config.SWAGGER_UI_DOC_EXPANSION = "list"
api = Api(
    app,
    title="ARGH",
    description="Augmented Roleplaying Game Helper - by @infra_naut et al",
    version=argh_version,
)


def memoize_with_expiry(expiry_time=0, cache={}):
    def _memoize_with_expiry(func, *args):
        key = args
        result = None
        if key in cache:
            result, timestamp = cache[key]
            # Check the age.
            age = time() - timestamp
            if not expiry_time or age < expiry_time:
                return result
        # this is actually a function I wrote / hacked together a very long time ago
        # this comment was here, I didn't even know I was getting retry for free, but lol
        # dialing it back to avoid long hangs
        # > if func breaks - looking at you, then try it again until shit works
        for i in range(3):
            try:
                result = func(*args)
                break
            except Exception as e:
                sleep(1 + random() * i)
                pass
        if result:
            cache[key] = (result, time())
        return result

    return decorator(_memoize_with_expiry)


if not hasattr(sys.stderr, "isatty"):
    # In GAE it's not defined and we must monkeypatch
    sys.stderr.isatty = lambda: False

import json

from flask import make_response


def jsonify(arg, status=200, indent=4, sort_keys=True, **kwargs):
    response = make_response(json.dumps(dict(arg), indent=indent, sort_keys=sort_keys))
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    response.headers["mimetype"] = "text/plain"
    response.status_code = status
    return response


class SimpleYDL(youtube_dl.YoutubeDL):
    def __init__(self, *args, **kargs):
        super(SimpleYDL, self).__init__(*args, **kargs)
        self.add_default_info_extractors()


def get_videos(url, extra_params):
    """
    Get a list with a dict for every video founded
    """
    ydl_params = {
        "format": "best",
        "cachedir": False,
        "logger": current_app.logger.getChild("youtube-dl"),
    }
    ydl_params.update(extra_params)
    ydl = SimpleYDL(ydl_params)
    res = ydl.extract_info(url, download=False)
    return res


def flatten_result(result):
    r_type = result.get("_type", "video")
    if r_type == "video":
        videos = [result]
    elif r_type == "playlist":
        videos = []
        for entry in result["entries"]:
            videos.extend(flatten_result(entry))
    elif r_type == "compat_list":
        videos = []
        for r in result["entries"]:
            videos.extend(flatten_result(r))
    return videos


def set_access_control(f):
    @functools.wraps(f)
    def wrapper(*args, **kargs):
        response = f(*args, **kargs)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    return wrapper


@api.errorhandler(youtube_dl.utils.DownloadError)
@api.errorhandler(youtube_dl.utils.ExtractorError)
def handle_youtube_dl_error(error):
    logging.error(traceback.format_exc())
    result = jsonify({"error": str(error)})
    result.status_code = 500
    return result


class WrongParameterTypeError(ValueError):
    def __init__(self, value, type, parameter):
        message = '"{}" expects a {}, got "{}"'.format(parameter, type, value)
        super(WrongParameterTypeError, self).__init__(message)


@api.errorhandler(WrongParameterTypeError)
def handle_wrong_parameter(error):
    logging.error(traceback.format_exc())
    result = jsonify({"error": str(error)})
    result.status_code = 400
    return result


def query_bool(value, name, default=None):
    if value is None:
        return default
    value = value.lower()
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        raise WrongParameterTypeError(value, "bool", name)


ALLOWED_EXTRA_PARAMS = {
    "format": str,
    "playliststart": int,
    "playlistend": int,
    "playlist_items": str,
    "playlistreverse": bool,
    "matchtitle": str,
    "rejecttitle": str,
    "writesubtitles": bool,
    "writeautomaticsub": bool,
    "allsubtitles": bool,
    "subtitlesformat": str,
    "subtitleslangs": list,
}


video_parser = reqparse.RequestParser()
video_parser.add_argument("url", type=str, help="URL to access.", required=True)
[
    video_parser.add_argument(k, type=v, required=False)
    for (k, v) in ALLOWED_EXTRA_PARAMS.items()
]

url_parser = reqparse.RequestParser()
url_parser.add_argument(
    "url", type=str, help="URL from which to display information", required=True
)


@api.route("/mm/info")
class Info(Resource):
    @api.expect(video_parser)
    def get(self):
        """" Get all info about all multimedia files at a given page. """
        args = video_parser.parse_args()
        result = get_videos(args.get("url"), args)
        if args.get("flatten"):
            result = flatten_result(result)
        return jsonify(result)


@api.route("/mm/play")
class Play(Resource):
    @api.expect(video_parser)
    def get(self):
        """ Play, stream, or save a video or other multimedia file! """
        args = video_parser.parse_args()
        result = get_videos(args.get("url"), args)
        url = result['formats'][-1]['url']
        return redirect(url)


@api.route("/mm/extractors")
class Extractors(Resource):
    def get(self):
        """ Return the list of supported multimedia extractor types. """
        ie_list = [
            {
                "name": ie.IE_NAME,
                "working": ie.working(),
            }
            for ie in youtube_dl.gen_extractors()
        ]
        return jsonify({"extractors": ie_list})


@api.route("/version")
class Version(Resource):
    def get(self):
        """ Get versions for youtube-dl, twint, and ARGH. """
        result = {
            "youtube-dl": youtube_dl_version,
            "argh": argh_version,
            "twint": utwee.twint_version,
        }
        return jsonify(result)


@api.route("/debug/get", doc=False)
class Get(Resource):
    @api.expect(url_parser)
    def get(self):
        args = url_parser.parse_args()
        res = urllib.request.urlopen(args.get("url")).read().decode()
        return Response(res, "text/html")


@api.route("/debug/headers", doc=False)
class Headers(Resource):
    def get(self):
        return jsonify(dict(self.headers))


tweep_parser = reqparse.RequestParser()

tweep_parser.add_argument(
    "username",
    type=str,
    help="Username whose timeline should be displayed.",
    required=True,
)
tweep_parser.add_argument(
    "limit", type=int, help="Number of tweets to be displayed.", required=False
)


@api.route("/tw/timeline")
class Tweep(Resource):
    @api.expect(tweep_parser)
    def get(self):
        """ Return a user's timeline (100 or specified number of tweets) as JSON for easy manipulation. """
        args = tweep_parser.parse_args()
        return Response(
            utwee.generate_response(args.get("username", args.get("limit") or 100)),
            mimetype="text/plain",
        )


metadata_cache = {}


@memoize_with_expiry(expiry_time=120, cache=metadata_cache)
def get_tweet_metadata_secret_api_bad_tech(status_id):
    # this is interesting, but a kinda terrible way of doing it...
    syndication_query = (
        "https://root.tweeter.workers.dev/tweet?host=cdn.syndication.twimg.com&id="
        + str(status_id)
    )
    synd_resp = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                syndication_query,
                headers={"User-Agent": choice(utwint.get.user_agent_list)},
            )
        ).read()
    )
    return synd_resp


embed_cache = {}


@memoize_with_expiry(expiry_time=120, cache=embed_cache)
def get_embed_by_id(status_id):
    oembed_query = (
        "http://root.tweeter.workers.dev/oembed?host=publish.twitter.com&dnt=true&omit_script=true&url=https://mobile.twitter.com/i/status/"
        + str(status_id)
    )
    embed_resp = json.loads(urllib.request.urlopen(oembed_query).read())
    return embed_resp


metadata_parser = reqparse.RequestParser()

metadata_parser.add_argument(
    "id", type=str, help="Tweet ID for which to display metadata.", required=True
)


@api.route("/tw/metadata")
class TwMetadata(Resource):
    @api.expect(metadata_parser)
    def get(self):
        """ Get all available metadata for a specified tweet (by URL or ID). """
        args = metadata_parser.parse_args()
        status_id = args.get("id")
        # if a URL was passed, grab the last fragment and pretend it's a status ID
        if "/" in status_id:
            status_id = status_id.strip("/").split("/")[-1]
        return jsonify(get_tweet_metadata_secret_api_bad_tech(status_id))


twreplies_parser = reqparse.RequestParser()
twreplies_parser.add_argument(
    "url", type=str, help="Tweet URL from which to display replies.", required=True
)
twreplies_parser.add_argument(
    "all", type=bool, help="Display all replies? (Default: just top replies)"
)


@api.route("/tw/replies")
class TwReplies(Resource):
    @api.expect(twreplies_parser)
    def get(self):
        """ Get all top-level replies (optionally: all) to a particular tweet as JSON. NB: Scrapes only nearest 250 timeline events, or up to one week. """
        args = twreplies_parser.parse_args()
        url, get_all = args.get("url"), args.get("all")
        if not (url and url.count("/") in (3, 5)):
            return Response(
                "Try again with ?url=https://twitter.com/account/status/..."
            )
        tweet_id = url.rstrip("/").split("/")[-1]
        username = url.rstrip("/").split("/")[-3]
        # very lame way of getting the date of the tweet with a single (albeit synchronous) request
        oembed_query = (
            "https://publish.twitter.com/oembed?dnt=true&omit_script=true&url=" + url
        )
        embed_resp = json.loads(urllib.request.urlopen(oembed_query).read())
        html = embed_resp.get("html") or ""
        if not html:
            return Response(f"Tweet {url} could not be found for embed.")
        date = html.split('ref_src=twsrc%5Etfw">')[-1].split("</a>")[0]
        (month, day, year) = date.split(" ")
        month_index = list(calendar.month_name).index(month)
        day = day.strip(",")
        day, year = int(day), int(year)
        # okay, now we have three integers - pass tem into an Arrow object, and use arrow's calculator to do the timeshifts.
        publish_date = arrow.Arrow(month=month_index, day=day, year=year)
        # instead of a week being 7 days, make it 8 days, bc I don't wanna think about timezones
        since = publish_date.shift(days=-1).format("YYYY-MM-DD")
        until = publish_date.shift(days=7).format("YYYY-MM-DD")
        # uh just roll with it, okay
        responses = [
            response
            for response in reversed(
                [
                    {
                        k: v for k, v in json.loads(r).items() if v
                    }  # just makes things shorter
                    for r in utwee.generate_response(
                        username, limit=250, since=since, until=until
                    )  # get 250 responses starting the day before the referenced tweet, ending 8 days after
                ]
            )
            if (
                response.get("conversation_id") == tweet_id
            )  # make sure it's part of the conversation
            and (
                get_all  # drop out if all=true
                or (
                    get_tweet_metadata_secret_api_bad_tech(response.get("id")).get(
                        "in_reply_to_status_id_str"
                    )
                    == tweet_id
                )
            )
        ]
        return Response(json.dumps(responses, indent=2), mimetype="text/plain")


if __name__ == "__main__":
    server_port = os.environ.get("PORT", "8080")
    app.run(debug=False, port=server_port, host="0.0.0.0")
