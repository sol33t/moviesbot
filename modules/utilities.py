import re
import logging

from rotten_tomatoes import RottenTomatoes
from google.appengine.api import urlfetch

def parse_text_for_imdb_ids(text):
    return re.findall(r'imdb.com/[\w\/]*title/(tt[\d]{7})/?',text)

"""
Given a blob of text, search for RT links and go to URL to 
get the Rotten Tomatoes ID
"""
def parse_text_for_rt_ids(text):
    ret = []
    rotten_urls = re.findall(r'(http://.+rottentomatoes.com/m/\w+/)',text)
    for url in rotten_urls:
        logging.debug("Found Rotten Tomatoes URL: %s" % url)
        # URL fetch to get the ID
        result = urlfetch.fetch(url)
        match = re.search(r'<meta name="movieID" content="(\d+)">',result.content)
        if match:
            rt_id = match.group(1)
            logging.info("Found Rotten Tomatoes id of: %s" % rt_id)
            ret.append(rt_id)
        else:
            logging.info("Couldn't find any movieID. Skipping this one")
    return ret

"""
Given a list of Rotten Tomatoes IDs, return a list of IMDB IDs
"""
def rotten_tomatoes_2_imdb(rt_ids):
    ret = []
    # Hack to have only unique ids in the list
    rt_ids = list(set(rt_ids))
    for rotten_id in rt_ids:
        rt = RottenTomatoes(rotten_id)
        imdb_id = rt.get_imdb_link()
        if imdb_id:
            ret.append(imdb_id)
    return ret