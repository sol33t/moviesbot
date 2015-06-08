# -*- coding: utf-8 -*- 

import logging
import urllib2
import datetime
import json

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from modules import search_cisi
from models import Movies, MovieTypes

class IMDB:

    def __init__(self, imdb_id=None):
        self.imdb_id = imdb_id
        if self.imdb_id is not None:
            date_search = datetime.datetime.now() - datetime.timedelta(days=7)
            imdb_data = self.get_imdb_data()
            if imdb_data is None or imdb_data.updated < date_search:
                urlfetch.set_default_fetch_deadline(45)
                self.response = self.api_call("http://omdbapi.com/?i=%s&plot=short&r=json&tomatoes=true" % imdb_id)
                logging.debug("Response is %s" % self.response)
                self.movie_data = self.add_movie_data()
                logging.debug("Type of this is %s" % self.movie_data.Type)
                if self.movie_data.Type == MovieTypes.movie:
                    self.add_cisi_data()
            else:
                logging.debug("Movie is already in NDB and data is less than 7 days old")
                self.movie_data = imdb_data


    def get_imdb_data(self):
        key = ndb.Key(Movies, self.imdb_id).get()
        if key:
            logging.debug("IMDB key in DB")
            logging.debug(key)
            return key
        else:
            logging.debug("IMDB key is not in the DB")
            return None

    def add_movie_data(self):
        movie = Movies (id=self.imdb_id)
        for thing, process_type in {
            'Title' : 'default',
            'Year' : 'int',
            'Poster' : 'default',
            'Released' : 'date',
            'DVD' : 'date',
            'Type' : 'type',
            'Season' : 'int',
            'Episode' : 'int',
            'seriesID' : 'default',
            'imdbID' : 'default',
            'imdbRating' : 'float',
            'imdbVotes' : 'int',
            'tomatoMeter' : 'int',
            'tomatoRating' : 'float',
            'tomatoReviews' : 'int',
            'tomatoFresh' : 'int',
            'tomatoRotten' : 'int',
            'tomatoUserMeter' : 'int',
            'tomatoUserRating' : 'float',
            'tomatoUserReviews' : 'int',
            'Metascore' : 'int'
        }.iteritems():
            logging.debug("Need to process %s as type %s" % (thing,process_type))
            if process_type is 'default':
                thing_value = self.get_thing(thing)
            elif process_type is 'int':
                thing_value = self.get_thing(thing)
                if thing_value:
                    thing_value = int(thing_value.replace(',','').split(u"–", 1)[0])
            elif process_type is 'float':
                thing_value = self.get_thing(thing)
                if thing_value:
                    thing_value = float(thing_value)
            elif process_type is 'date':
                thing_value = self.get_thing_date(thing)
            elif process_type is 'type':
                thing_value = self.get_thing_type(thing)
            else:
                thing_value = None
            logging.info("Setting self.%s to be %s" % (thing,thing_value))
            setattr(movie,thing,thing_value)
        movie.put()
        return movie

    def add_cisi_data(self):
        # Search movie ID from CISI
        logging.info("Going to search CISI for %s" % self.movie_data.Title)
        cisi_movie = search_cisi(
            movie=self.movie_data.Title,
            imdb_id=self.imdb_id,
            movie_year=self.movie_data.Year
        )
        if cisi_movie:
            self.movie_data.CISIid = cisi_movie['_id']
            self.movie_data.CISIurl = cisi_movie['links']['shortUrl']
            if 'rottentomatoes' in cisi_movie['links']:
                self.movie_data.tomatoURL = cisi_movie['links']['rottentomatoes']
            self.movie_data.put()
        else:
            logging.warning("No CISI results for %s with imdb_id %s" % (self.movie_data.Title,self.imdb_id))

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

    def get_thing_type(self,thing):
        movie_type = self.get_thing(thing)
        return getattr(MovieTypes, movie_type)

    def get_thing_date(self,thing):
        date_string = self.get_thing(thing)
        if date_string:
            imdb_date = datetime.datetime.strptime(date_string, '%d %b %Y')
            return imdb_date
        else:
            return None

    def get_thing(self,thing):
        if thing in self.response and self.response[thing] != 'N/A':
            ret = self.response[thing]
            logging.debug("Looked up %s in the response. Returning back %s" % (thing, ret))
            return ret 
        else:
            logging.debug("Unable to find %s in the response, or it was set to N/A" % thing)
            return None