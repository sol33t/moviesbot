import urllib
import json
import logging
from google.appengine.api import urlfetch
from utilities import parse_text_for_imdb_ids

"""
Returns a CISI object for the movie name given
Uses optional IMDB ID to narrow down if there are multiple results
Returns False on error or if there is no IMDB match on a long list
"""
def search_cisi(movie,imdb_id=None,movie_year=None):
    # Some string replacement on the movie title needed
    if movie[0] == "+":
        movie = movie.replace('+','plus ')
        logging.info("Title starts with +. Renaming movie to %s" %movie)
    urlfetch.set_default_fetch_deadline(45)
    result = urlfetch.fetch('http://www.canistream.it/services/search?movieName=%s' % urllib.quote_plus(movie))
    json_result = json.loads(result.content)
    if result.status_code != 200:
        return False
    # If no imdb link or year, then return first result
    if imdb_id is None and movie_year is None:
        logging.info("We have little data to go on. Just returning first Can I Stream It result")
        return json_result[0]
    else:
        for movie in json_result:
            # If the first movie doesn't have an imdb link, hope it's the right one
            if 'imdb' not in movie['links']:
                logging.info("No IMDB link for %s" % movie['title'])
                logging.info("IMDB says year is %s and CISI says year is %s" % (movie_year,movie['year']))
                if int(movie_year) == int(movie['year']):
                    logging.info("IMDB isn't set but Can I Stream it matches year, about...")
                    return movie
            else:
                movie_imdb_id = parse_text_for_imdb_ids(movie['links']['imdb'])
                if imdb_id == movie_imdb_id[0]:
                    logging.info("IMDB ID matches with Can I Stream it")
                    return movie
    return False

def get_movie_info(movie_id,movie_type):
    urlfetch.set_default_fetch_deadline(45)
    url = 'http://www.canistream.it/services/query?movieId=%s&attributes=1&mediaType=%s' % (movie_id, movie_type)
    logging.debug("Looking up CISI info for a %s option for movie %s. URL is: %s" %(movie_type,movie_id,url))
    result = urlfetch.fetch(url)
    logging.debug("Got back the following from CISI search: %s" % result.content)
    return json.loads(result.content)

def parse_movie_info(results):
    ret = []
    for site in results:
        name = results[site]['friendlyName']
        if results[site]['price'] > 0:
            name = "%s - $%s" % (results[site]['friendlyName'], results[site]['price'])
        string = "[%s](%s)" % ( name, results[site]['url'] )
        ret.append(string.replace(' ','&nbsp;'))
    return ret