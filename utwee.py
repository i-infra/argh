import threading
from queue import Queue

import utwint as twint

twint_version = twint.__version__

import asyncio


class StreamWriter(object):
    def __init__(self, limit=100):
        self.queue = Queue()
        self.limit = limit

    def write(self, s):
        self.queue.put(s)

    def read(self):
        s = self.queue.get()
        self.queue.task_done()
        if s == "~":
            return None
        if self.limit == 0:
            return None
        self.limit -= 1
        return s

    def close(self, whatever=None):
        self.write("~")  # indicate EOF


import json


class DummyWriter(object):
    def __init__(self, limit=100):
        self.queue = Queue()
        self.limit = limit

    def write(self, s):
        print(json.dumps(s))

    def close(self, whatever=None):
        self.write("~")  # indicate EOF


def run_search(username="jack", limit=100, since=None, until=None, Writer=DummyWriter):
    if limit == None:
        limit = 100
    sw = Writer(limit)

    def search_task():
        tc = twint.Config()
        tc.All = username
        tc.Store_object = False
        tc.Store_dict = True
        tc.Output = sw
        tc.Debug = False
        tc.Hide_output = True
        tc.Stats = True
        tc.Since = since
        tc.Until = until
        tc.Limit = limit + 20
        twint.run.Search(tc, callback=sw.close)

    threading.Thread(target=search_task).start()
    while True:
        chunk = sw.read()
        if chunk is None:
            break
        yield chunk


def run_users(usernames="jack"):

    try:
        asyncio.get_event_loop()
    except RuntimeError as e:
        if "no current event loop" in str(e):
            asyncio.set_event_loop(asyncio.new_event_loop())
    tc = twint.Config()
    tc.Lookup = True
    tc.Store_object = True
    tc.Store_object_users_list = []
    tc.Output = None
    tc.Debug = False
    tc.Hide_output = True
    if "," not in usernames:
        usernames += ","

    tw = twint.run.Twint(tc)
    for username in usernames.split(","):
        tw.token.refresh()
        if username:
            tc.Username = username
            asyncio.get_event_loop().run_until_complete(tw.main())
    for user in tc.Store_object_users_list:
        yield user
