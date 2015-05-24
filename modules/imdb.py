import logging
import json
from google.appengine.api import urlfetch

class IMDB:

    def __init__(self, imdb_id=None):
        if imdb_id is not None:
            urlfetch.set_default_fetch_deadline(45)
            self.response = self.api_call("http://www.omdbapi.com/?i=%s&plot=short&r=json&tomatoes=true" % imdb_id)
            logging.debug("Response is %s" % self.response)

    def api_call(self,url):
        result = urlfetch.fetch(url)
        if result.status_code == 200:
            json_ret = json.loads(result.content)
            return json_ret
        else:
            logging.error("The IMDB Api call returned with status code %d" % result.status_code)
            return False

    def get_thing(self,thing):
        if thing in self.response:
            return self.response[thing]
        else:
            return False