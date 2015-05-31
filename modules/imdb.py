import logging
import urllib2
import json
from google.appengine.api import urlfetch

class IMDB:

    def __init__(self, imdb_id=None):
        if imdb_id is not None:
            urlfetch.set_default_fetch_deadline(45)
            self.response = self.api_call("http://omdbapi.com/?i=%s&plot=short&r=json&tomatoes=true" % imdb_id)
            logging.debug("Response is %s" % self.response)

    def api_call(self,url):
        try:
            result = urlfetch.fetch(url)
        except urllib2.URLError, e:
            logging.error("Couldn't fetch info from OMDB")
            return None
        if result.status_code == 200:
            json_ret = json.loads(result.content)
            return json_ret
        else:
            logging.error("The IMDB Api call returned with status code %d" % result.status_code)
            return None

    def get_thing(self,thing):
        if thing in self.response:
            return self.response[thing]
        else:
            return False