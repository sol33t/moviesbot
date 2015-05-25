import logging
import json
import config
from google.appengine.api import urlfetch

class RottenTomatoes:

    def __init__(self, rottentomatoes_id=None):
        if rottentomatoes_id:
            urlfetch.set_default_fetch_deadline(45)
            self.response = self.api_call('movies',rottentomatoes_id)
            logging.debug("Response is %s" % self.response)

    def api_call(self,endpoint,rottentomatoes_id):
        try:
            result = urlfetch.fetch("http://api.rottentomatoes.com/api/public/v1.0/%s/%s.json?apikey=%s" % (
                endpoint,
                rottentomatoes_id,
                config.rottentomatoes['key']
            ))
        except urllib2.URLError, e:
            logging.error("Couldn't fetch info from OMDB")
            return None
        if result.status_code == 200:
            json_ret = json.loads(result.content)
            return json_ret
        else:
            logging.error("The Rotten Tomatoes Api call returned with status code %d" % result.status_code)
            return None

    def get_imdb_link(self):
        if 'alternate_ids' in self.response and 'imdb' in self.response['alternate_ids']:
            imdb_id = self.response['alternate_ids']['imdb']
            logging.debug("The IMDB ID is: %s" % imdb_id)
            return "tt%s" % imdb_id
        else:
            return None