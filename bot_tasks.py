import webapp2
import urllib
import base64
import json
import logging
import datetime
import time
import yaml
import re
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from uuid import uuid4

REDDIT_PM_IGNORE = "http://bit.ly/ignoreredditmoviesbot"
REDDIT_PM_DELETE = "http://reddit.com/message/compose/?to=moviesbot&subject=delete&message=delete%20{thing_id}"
NO_BREAK_SPACE = u'&nbsp;'
MAX_MESSAGE_LENGTH = 10000

SIG_LINKS = [
    u'[](#bot)',
    u'[Stop%sReplying](%s)' % (NO_BREAK_SPACE, REDDIT_PM_IGNORE),
    u'[Delete](%s)' % REDDIT_PM_DELETE,
    u'[](#bot)'
]

urlfetch.set_default_fetch_deadline(45)
with open("config.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

class Reddit:

    def __init__(self):
        self.get_token()

    def get_token(self):
        base64creds = base64.b64encode(cfg['reddit']['client_id'] + ":" + cfg['reddit']['client_secret'])
        request_payload = {"grant_type": "password",
            "duration": "permanent",
            "username": cfg['reddit']['user'],
            "password": cfg['reddit']['password']
        }
        request_payload_encoded = urllib.urlencode(request_payload)
        headers={"Authorization": 
            "Basic %s" % base64creds
        }
        result = urlfetch.fetch("https://ssl.reddit.com/api/v1/access_token",
            payload=request_payload_encoded,
            method=urlfetch.POST,
            headers=headers,
        )
        if result.status_code == 200:
            auth_token = json.loads(result.content)
            logging.debug(auth_token)
            if 'error' in auth_token:
                logging.error("Got the following error: %s" % token_json['error'])
                return False
            else:
                logging.info("Setting auth token")
                self.auth_token = auth_token["access_token"]
                self.auth_expires = int(time.time())+auth_token['expires_in']
                return True
        else:
            logging.error("Got the following status code: %s" % result.status_code)
            return False

    def make_headers(self):
        if int(time.time()) > self.auth_expires:
            # We've had this auth token for longer than an hour
            # Need to refresh the auth
            if not self.get_token():
                logging.error("Error when refreshing auth token")
        headers = {
            "Authorization": "bearer " + self.auth_token,
            "User-Agent": "moviesbot version 0.0.1 by /u/moviesbot"
        }
        return headers


    def api_call(self,url,payload=None):
        if not self.auth_token:
            logging.error("Not authenticated. What are you doing!")
            return False
        headers = self.make_headers()
        if payload is not None:
            method=urlfetch.POST
        else:
            method=urlfetch.GET
        result = urlfetch.fetch(url, method=method, payload=payload, headers=headers)
        logging.debug(result.content)
        if result.status_code == 200:
            return json.loads(result.content)
        elif result.status_code == 401:
            logging.warning("Looks like the token expired")
        else:
            logging.error("The api call returned with status code %d for the following URL:%s" % (result.status_code,url))
            return False

    def get_user_info(self):
        return self.api_call("https://oauth.reddit.com/api/v1/me")

    def search_reddit(self,query,sort='new',time='hour'):
        subreddits = ""
        restrict_sr = ""
        if 'whitelisted_subreddits' in cfg:
            subreddits = "r/" + "+".join(cfg['whitelisted_subreddits']) + "/"
            restrict_sr = "&restrict_sr=on"
        url = "https://oauth.reddit.com/%ssearch.json?q=%s%s&sort=%s&t=%s" % (subreddits,query,restrict_sr,sort,time)
        logging.info("Performing search on Reddit to the following URL: %s" % url)
        return self.api_call (url)

    def post_to_reddit(self,thing_id,text,post_type='comment'):
        logging.info("Posting comment to reddit post %s" % thing_id)
        logging.debug("Text is %s" % text)
        url = "https://oauth.reddit.com/api/%s/.json" % post_type
        payload = { 'thing_id':thing_id,
                    'text':text,
                    'api_type':'json'
        }
        return self.api_call(url,urllib.urlencode(payload))

    def delete_from_reddit(self,thing_id):
        url = "https://oauth.reddit.com/api/del"
        payload = urllib.urlencode({'id':thing_id})
        logging.debug(payload)
        if self.api_call(url,payload) is not False:
            return True
        else:
            return False

    def get_unread_messages(self):
        url = "https://oauth.reddit.com/message/unread"
        return self.api_call (url)

    def mark_message_read(self,messages):
        url = "https://oauth.reddit.com/api/read_message"
        payload = urllib.urlencode({'id':messages})
        logging.debug(payload)
        if self.api_call(url,payload) is not False:
            return True
        else:
            return False

    def send_message(self,to,subject,text):
        url = "https://oauth.reddit.com/api/compose"
        payload = {
            'to': to,
            'subject':subject,
            'text':text,
            'api_type':'json'
        }
        return self.api_call(url,payload)


class Post(ndb.Model):
    post_id = ndb.IntegerProperty()
    comment_id = ndb.IntegerProperty()
    reply_id = ndb.IntegerProperty()
    author = ndb.StringProperty()
    permalink = ndb.StringProperty()
    deleted = ndb.BooleanProperty(default=False)
    movies = ndb.StringProperty(repeated=True)
    post_date = ndb.DateTimeProperty()
    reply_date = ndb.DateTimeProperty(auto_now_add=True)

class IgnoreList(ndb.Model):
    author = ndb.StringProperty()
    ignored = ndb.BooleanProperty(default=True)
    body = ndb.TextProperty()
    message_id = ndb.IntegerProperty()
    message_date = ndb.DateTimeProperty()
    update_date = ndb.DateTimeProperty(auto_now_add=True)

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
            loggine.error("The IMDB Api call returned with status code %d" % result.status_code)
            return False

    def get_title(self):
        if 'Title' in self.response:
            return self.response['Title']
        else:
            return False

    def get_rating(self):
        if 'imdbRating' in self.response:
            return self.response['imdbRating']
        else:
            return False

    def get_year(self):
        if 'Year' in self.response:
            return self.response['Year']
        else:
            return False

    def get_type(self):
        if 'Type' in self.response:
            return self.response['Type']
        else:
            return False

    def get_tomato_meter(self):
        if 'tomatoMeter' in self.response:
            return self.response['tomatoMeter']
        else:
            return False

def parse_text_for_imdb_ids(text):
    return re.findall(r'imdb.com/[\w\/]*title/(tt[\d]{7})/?',text)

def get_imgur_album_images(album_id):
    headers = {"Authorization": "Client-ID "+ cfg['imgur']['client_id']}
    result = urlfetch.fetch("https://api.imgur.com/3/album/%s/images" % album_id, headers=headers)
    return json.loads(result.content)

# Returns a CISI object for the movie name given
# Uses optional IMDB ID to narrow down if there are multiple results
# Returns False on error or if there is no IMDB match on a long list
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
    if imdb_id is None and imdb_year is None:
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
    result = urlfetch.fetch('http://www.canistream.it/services/query?movieId=%s&attributes=1&mediaType=%s' % (movie_id, movie_type))
    return json.loads(result.content)

def parse_movie_info(results):
    ret = []
    for site in results:
        if results[site]['price'] > 0:
            string = "[%s - $%s](%s)" % ( results[site]['friendlyName'], results[site]['price'], results[site]['url'] )
        else:
            string = "[%s](%s)" % ( results[site]['friendlyName'], results[site]['url'] )
        ret.append(string.replace(' ','&nbsp;'))
    return ret

def is_author_ignored(author):
    author_ignored = IgnoreList.query(ndb.AND(
        IgnoreList.author == author,
        IgnoreList.ignored == True
    )).fetch()
    if not author_ignored:
        return False
    else:
        return True

def author_ignore_key(author):
    author_ignored = IgnoreList.query(IgnoreList.author == author).get()
    if not author_ignored:
        return False
    else:
        return author_ignored

def get_movie_data(movies):
    media_types = cfg['mediatypes']
    movies_ret = []
    for imdb_id in movies:
        logging.info("Looking up information for IMDB id: %s" %imdb_id)
        movie_obj = {}
        # Lookup IMDB name
        imdb_obj = IMDB(imdb_id)
        imdb_title = imdb_obj.get_title()
        imdb_year = imdb_obj.get_year()
        rt_tomatometer = imdb_obj.get_tomato_meter()
        if imdb_title is False:
            logging.warning("Couldn't get IMDB info for IMDB id: %s" %imdb_id)
            continue
        if imdb_obj.get_type() != "movie":
            logging.warning("%s is not a movie. Not going to proceed with this title" % imdb_title)
            continue
        # Get IMDB Rating
        imdb_rating = imdb_obj.get_rating()
        # Search movie ID from CISI
        logging.info("Going to search CISI for %s" %imdb_title)
        cisi_movie = search_cisi(imdb_title,imdb_id,imdb_year)
        if cisi_movie:
            movie_obj = cisi_movie
            movie_obj['imdb_rating'] = imdb_rating
            movie_obj['imdb_id'] = imdb_id
            movie_obj['imdb_title'] = imdb_title
            movie_obj['tomatoMeter'] = rt_tomatometer
            cisi_movie_id = cisi_movie['_id']
            # Search for CISI Streaming/Rental/Buy
            exclude = True
            for media_type in media_types:
                logging.info("Going up to look up %s info for CISI movie ID: %s" % (media_type,cisi_movie_id))
                movie_obj[media_type] = get_movie_info( cisi_movie_id , media_type.lower() )
                if movie_obj[media_type]:
                    exclude = False
            if not exclude:
                movies_ret.append(movie_obj)
            else:
                logging.warning("No results for all media types. Not including this movie in the list")
        else:
            logging.warning("No CISI results for %s with imdb_id %s" % (imdb_title,imdb_id))
    # Return Object
    return movies_ret

def comment_on_post(post):
    movies_list = []
    comment_id = None
    error_commenting = False
    int_id = int(post['data']['id'],36)
    name = post['data']['name']
    author = post['data']['author']
    permalink = post['data']['permalink']
    selftext = post['data']['selftext']
    post_date = datetime.datetime.fromtimestamp(int(post['data']['created_utc']))
    post_key = ndb.Key('Post',int_id).get()
    # If we never commented on this post
    if post_key is None:
        # If this user isn't on the ignore list
        if not is_author_ignored(author):
            logging.info("Need to process post %s" % permalink)
            list_of_movies = parse_text_for_imdb_ids(post['data']['selftext'])
            list_of_movies += parse_text_for_imdb_ids(post['data']['url'])
            list_of_movies += parse_text_for_imdb_ids(post['data']['title'])
            movies_data = get_movie_data(list(set(list_of_movies)))
            if movies_data:
                for movie in movies_data:
                    movies_list.append(movie['imdb_id'])
                comment_text = format_new_post(movies_data)
                logging.debug(comment_text)
                new_post_result =  reddit.post_to_reddit(name,comment_text,'comment')
                if new_post_result:
                    comment_id = int(new_post_result['json']['data']['things'][0]['data']['id'],36)
                    # get the name of the comment
                    comment_name = new_post_result['json']['data']['things'][0]['data']['name']
                    updated_comment_text = comment_text.format(thing_id=comment_name)
                    reddit.post_to_reddit(comment_name,updated_comment_text,'editusertext')
                else:
                    error_commenting = True
                    logging.error("Couldn't comment. Not marking this as commented in DB")
            else:
                logging.warning("No movie data was found for post %s" % name)
            if not error_commenting:
                    post_key = Post(
                        id = int_id,
                        post_id = int_id,
                        comment_id = comment_id,
                        post_date = post_date,
                        author = author,
                        permalink = permalink,
                        movies = movies_list
                    ).put()
                    logging.info("Added %s to the db. Will not comment on this post again" % name)
            else:
                logging.warning("An error was encountered with %s. Not adding this post to the DB in hope a subsequent run will fix the issue" % name)
        else:
            logging.info("Reply on %s skipping. %s would prefer to be ignored" % (name,author))

def format_new_post(movies_data):
    default_media_types = cfg['mediatypes']
    media_types=[]
    for media_type in default_media_types:
        type_in_data = False
        for movie in movies_data:
            if movie[media_type]:
                type_in_data = True
        if type_in_data:
            media_types.append(media_type)
    ret_line = ["Here's where you can stream/rent/buy the movie(s) listed:\n\n"]
    heading = ['Title','IMDB','Rotten Tomatoes']
    heading += media_types
    seperator = []
    for index, w in enumerate(heading):
        sep = "---"
        if index > 1:
            sep+=":"
        seperator.append(sep)
    ret_line.append(" | ".join(heading))
    ret_line.append("|".join(seperator))
    for movie in movies_data:
        short_url = movie['links']['shortUrl']
        title = movie['imdb_title']
        rt_rating = movie['tomatoMeter']
        rt_link = movie['links']['rottentomatoes']
        imdb_rating = movie['imdb_rating']
        imdb_link = "http://www.imdb.com/title/%s/" % movie['imdb_id']
        line = ["**[%s](%s)**" % (title.replace(' ','&nbsp;'), short_url)]
        line.append("[%s](%s)" % (imdb_rating,imdb_link))
        line.append("[{0}%]({1})".format(rt_rating,rt_link))
        for media_type in media_types:
            type_strings = parse_movie_info(movie[media_type])
            type_joined = ' '.join(type_strings)
            line.append(type_joined)
        ret_line.append('|'.join(line))
    ret_line.append('---\n' + ' ^| '.join(['^' + a for a in SIG_LINKS]))
    return "\n".join(ret_line)

def ignore_message(message):
    response = None
    author  = message['author']
    body    = message['body']
    date    = datetime.datetime.fromtimestamp(int(message['created_utc']))
    subject = message['subject'].lower()
    message_id = int(message['id'],36)
    # If subject == IGNORE ME
    if subject == "ignore me":
        if is_author_ignored(author):
            # We're already ignoring this user.
            logging.info("Request to ignore %s when already ignoring this user. Skipping" % author)
            ignored = True
        else:
            # Add username to DB to be ignored
            logging.info("Adding %s to the ignore list" % author)
            ignored = True
            response =  (
                "Sorry to hear you want me to ignore you. Was it something "
                "I said? I will not reply to any posts you make in the future. "
                "If you want me to reply to your posts, you can send me "
                "[a message](bit.ly/rememberredditmoviesbot). Also, if you "
                "wouldn't mind filling out this survey giving me feedback, "
                "I'd really appreciate it. It would make me a better bot"
            )
    # If subject ==  REMEMBER ME
    elif subject == "remember me":
        # Remove username from DB
        logging.info("No longer ignoring %s" % author)
        ignored = False
        response = (
            "Ok, I'll reply to your posts from now on. "
            "If you want me to stop, you can send me "
            "[a message](http://bit.ly/ignoreredditmoviesbot), "
            "and I'll stop replying to your posts"
        )
    ignore_key = author_ignore_key(author)
    if not ignore_key:
        ignore_key = IgnoreList()
    ignore_key.message_id = message_id
    ignore_key.message_date = date
    ignore_key.body = body
    ignore_key.author = author
    ignore_key.ignored = ignored
    ignore_key.put()
    return response

def delete_message(message):
    response = None
    author = message['author']
    body = message['body']
    body_regex = re.search(r'delete ((t\d+)_(\w+))',body)
    thing_name = body_regex.group(1)
    thing_type = body_regex.group(2)
    thing_id = int(body_regex.group(3),36)
    # Figure out what the thing they want us to delete is
    if thing_type == "t1":
        # This thing is a comment
        # Lookup this thing in the DB
        post = Post.query(Post.comment_id == thing_id).get()
        if post:
            original_author = post.author
            # If the author is the same as the author in question
            if original_author == author:
                logging.info("Message from %s matches OP %s. Will delete %s" %(author,original_author,thing_name))
                # Delete post
                reddit.delete_from_reddit(thing_name)
                post.deleted = True
                post.put()
            else:
                # Delete request isn't from OP. Don't delete
                logging.info("%s isn't the OP. Will not delete %s" % (author,thing_name))
        else:
            # Probably shoudn't error in this case
            logging.error("Couldn't find a post corrsponding to %s in the DB" % thing_name)
    else:
        # Probably shoudn't error in this case
        logging.error("Received Delete request for unknown thing type %s" % thing_type)
    return response

reddit = Reddit()

class search_posts(webapp2.RequestHandler):
    def get(self):
        search_results = reddit.search_reddit("title%3Aimdb.com+OR+url%3Aimdb.com+OR+imdb.com",time='all')
        if search_results:
            for post in search_results['data']['children']:
                # If subreddit is not on block list
                comment_on_post(post)

class read_messages(webapp2.RequestHandler):
    def get(self):
        logging.info("Getting list of unread messages")
        # Get unread messages
        unread = reddit.get_unread_messages()
        if not unread:
            logging.error("Error getting unread messages")
            return True
        logging.debug("Received the following response for unread messages %s" % unread)
        for message in unread['data']['children']:
            response = None
            author = message['data']['author']
            name = message['data']['name']
            if not message['data']['was_comment']:
                subject = message['data']['subject'].lower()
                logging.info("Got a message from %s with the subject %s" % (author,subject))
                if subject in ["ignore me", "remember me"]:
                    ignore_message(message['data'])
                elif subject == "delete":
                    delete_message(message['data'])
            # Mark message as read
            if reddit.mark_message_read(name):
                if response is not None:
                    # Reply to the user
                    reply_subject = "re: %s" %subject
                    logging.info("Replying with subject: %s and response %s" % (reply_subject,response))
                    reddit.send_message(author,reply_subject,response)

application = webapp2.WSGIApplication([
    ('/tasks/search/imdb', search_posts),
    ('/tasks/inbox', read_messages)
],
    debug=True
)
