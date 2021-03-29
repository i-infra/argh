import utwint as twint
from queue import Queue
import threading

twint_version = twint.__version__

class StreamWriter(object):
    def __init__(self, limit=100):
        self.queue = Queue()
        self.limit = limit

    def write(self, str):
        self.queue.put(str)

    def read(self):
        s = self.queue.get()
        self.queue.task_done()
        if s == '~':
            return None
        if self.limit == 0:
            return None
        self.limit -= 1
        return s

    def close(self):
        self.write('~')  # indicate EOF


def generate_response(user_name, limit=100):
    sw = StreamWriter(limit=100)
    def task():
        tc = twint.Config()
        tc.All=user_name
        tc.Store_object = True
        tc.Store_json = True
        tc.Output = sw
        tc.Debug = True
        tc.Hide_output = True
        tc.Stats = True
        tc.Limit = limit+20
        twint.run.Search(tc)
    threading.Thread(target=task).start()
    while True:
        chunk = sw.read()
        if chunk is None:
            break
        yield chunk
