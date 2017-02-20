from protorpc import messages
from protorpc import message_types

from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop

class Post(ndb.Model):
    post_id = ndb.IntegerProperty()
    post_kind = ndb.StringProperty()
    name = ndb.StringProperty(indexed=True)
    author = ndb.StringProperty()
    permalink = ndb.StringProperty()
    subreddit = ndb.StringProperty()
    movies = ndb.KeyProperty(repeated=True)
    movies_list = ndb.StringProperty(repeated=True)
    post_date = ndb.DateTimeProperty()
    processing = ndb.BooleanProperty(default=False)
    commented = ndb.BooleanProperty(default=False)
    added = ndb.DateTimeProperty(auto_now_add=True)

class Comment(ndb.Model):
    name = ndb.StringProperty()
    post_date = ndb.DateTimeProperty(auto_now_add=True)
    score = ndb.IntegerProperty()
    deleted = ndb.BooleanProperty(default=False)
    updated = ndb.DateTimeProperty(auto_now=True)
    revision = ndb.IntegerProperty()

class CommentRevisions(ndb.Model):
    body = ndb.TextProperty()
    reply_date = ndb.DateTimeProperty(auto_now_add=True)

class IgnoreList(ndb.Model):
    author = ndb.StringProperty()
    ignored = ndb.BooleanProperty(default=True)
    body = ndb.TextProperty()
    message_id = ndb.IntegerProperty()
    message_date = ndb.DateTimeProperty()
    update_date = ndb.DateTimeProperty(auto_now_add=True)

class Whitelisted(ndb.Model):
    subreddit = ndb.StringProperty()
    updated = ndb.DateTimeProperty(auto_now_add=True)
    updated_by = ndb.StringProperty()

class Blacklisted(ndb.Model):
    subreddit = ndb.StringProperty()
    updated = ndb.DateTimeProperty(auto_now_add=True)
    updated_by = ndb.StringProperty()

class CISITypes(messages.Enum):
    streaming = 1
    rental    = 2
    purchase  = 3
    dvd       = 4
    xfinity   = 5

class CISI(ndb.Model):
    cisi_type = msgprop.EnumProperty(CISITypes)
    cisi_id = ndb.StringProperty()
    url = ndb.StringProperty()
    price = ndb.FloatProperty()
    external_id = ndb.StringProperty()
    date_checked = ndb.DateTimeProperty()
    direct_url = ndb.StringProperty()
    friendlyName = ndb.StringProperty()
    added = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

class MovieTypes(messages.Enum):
    movie   = 1
    series  = 2
    episode = 3
    game    = 4

class Movies(ndb.Model):
    Title = ndb.StringProperty()
    Year = ndb.IntegerProperty()
    Poster = ndb.StringProperty()
    Released = ndb.DateTimeProperty()
    DVD = ndb.DateTimeProperty()
    Type = msgprop.EnumProperty(MovieTypes)
    Season = ndb.IntegerProperty()
    Episode = ndb.IntegerProperty()
    seriesID = ndb.StringProperty()
    imdbID = ndb.StringProperty()
    imdbRating = ndb.FloatProperty()
    imdbVotes = ndb.IntegerProperty()
    tomatoURL = ndb.StringProperty()
    tomatoMeter = ndb.IntegerProperty()
    tomatoRating = ndb.FloatProperty()
    tomatoReviews = ndb.IntegerProperty()
    tomatoFresh = ndb.IntegerProperty()
    tomatoRotten = ndb.IntegerProperty()
    tomatoUserMeter = ndb.IntegerProperty()
    tomatoUserRating = ndb.FloatProperty()
    tomatoUserReviews = ndb.IntegerProperty()
    Metascore = ndb.IntegerProperty()
    mhid = ndb.StringProperty()
    mh_name = ndb.StringProperty()
    mh_altId = ndb.StringProperty()
    added = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)