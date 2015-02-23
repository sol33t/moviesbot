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

REDDIT_PM_IGNORE   = "http://www.reddit.com/message/compose/?to=moviesbot&subject=IGNORE%20ME&message=[IGNORE%20ME](http://i.imgur.com/s2jMqQN.jpg\)"
REDDIT_PM_REMEMBER = "http://www.reddit.com/message/compose/?to=moviesbot&subject=REMEMBER%20ME&message=I%20made%20a%20mistake%20I%27m%20sorry,%20will%20you%20take%20me%20back"
REDDIT_PM_DELETE   = "http://reddit.com/message/compose/?to=moviesbot&subject=delete&message=delete%20{thing_id}"
REDDIT_PM_FEEDBACK = "https://docs.google.com/forms/d/1PZTwDM71_Wiwxdq6NGKHI1zf-GC2oahqxwn8tX-Hq_E/viewform"
REDDIT_PM_MODS     = "https://www.reddit.com/r/moviesbot/wiki/faq#wiki_info_for_moderators"
REDDIT_FAQ         = "https://www.reddit.com/r/moviesbot/wiki/faq"
SOURCE_CODE        = "https://github.com/stevenviola/moviesbot"
NO_BREAK_SPACE = u'&nbsp;'
MAX_MESSAGE_LENGTH = 10000

SIG_LINKS = [
    '[](#bot)',
    '[Stop%sReplying](%s)' % (NO_BREAK_SPACE, REDDIT_PM_IGNORE),
    '[Delete](%s)' % REDDIT_PM_DELETE,
    '[FAQ](%s)' % REDDIT_FAQ,
    '[Source](%s)' % SOURCE_CODE,
    ('Created{s}and{s}maintained{s}by{s}/u/stevenviola').format(s=NO_BREAK_SPACE),
    '[](#bot)'
]

urlfetch.set_default_fetch_deadline(45)
with open("config.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

class Reddit:

    def __init__(self):
        if self.get_token() is True:
            user_info = self.get_user_info()
            if user_info is not False:
                username = user_info['name']
                link_karma = user_info['link_karma']
                comment_karma = user_info['comment_karma']
                logging.info("Starting up running as %s. User has %s link karma and %s comment karma" %(username,link_karma,comment_karma))
            else:
                logging.error("Error inilitizing with Reddit and user %s" % cfg['reddit']['user'])
        else:
            logging.error("Could not get auth token")

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
            logging.info(auth_token)
            if 'error' in auth_token:
                self.auth_token = False
                logging.error("Got the following error: %s" % auth_token['error'])
                return False
            else:
                logging.info("Setting auth token")
                self.auth_token = auth_token["access_token"]
                self.auth_expires = int(time.time())+auth_token['expires_in']
                return True
        else:
            logging.error("Got the following status code: %s" % result.status_code)
            self.auth_token = False
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
            logging.warning("Woah, not authenticated. Will try to get auth_token")
            if not self.get_token():
                logging.error("Couldn't get auth token. Aborting API Call")
                return False
        headers = self.make_headers()
        if payload is not None:
            method=urlfetch.POST
        else:
            method=urlfetch.GET
        result = urlfetch.fetch(url, method=method, payload=payload, headers=headers)
        if result.status_code == 200:
            return json.loads(result.content)
        elif result.status_code == 401:
            logging.warning("Looks like the token expired")
            # Get a new token here
            self.get_token()
        else:
            logging.error("The api call returned with status code %d for the following URL:%s" % (result.status_code,url))
        return False

    def get_user_info(self):
        return self.api_call("https://oauth.reddit.com/api/v1/me")

    def is_user_moderator(self,subreddit,user):
        url = "https://oauth.reddit.com/r/%s/about/moderators.json" % (subreddit)
        moderators = self.api_call(url)
        for moderator in moderators['data']['children']:
            if moderator['name'] == user:
                return True
        return False

    def search_reddit(self,query,sort='new',time='hour'):
        url = "https://oauth.reddit.com/search.json?q=%s&sort=%s&t=%s" % (query,sort,time)
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
        unread_messages = self.api_call (url)
        if unread_messages:
            return unread_messages
        else:
            return False

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
        payload = urllib.urlencode({
            'to': to,
            'subject':subject,
            'text':text,
            'api_type':'json'
        })
        logging.info("Sending the following payload: %s" % payload)
        return self.api_call(url,payload)

    def update_wiki(self,subreddit,page,content,reason):
        url = "https://oauth.reddit.com/r/%s/api/wiki/edit" % subreddit
        payload = urllib.urlencode({
            'content': content,
            'page':page,
            'reason':reason
        })
        logging.info("Sending the following payload: %s" % payload)
        return self.api_call(url,payload)

class Post(ndb.Model):
    post_id = ndb.IntegerProperty()
    post_kind = ndb.StringProperty()
    comment_id = ndb.IntegerProperty()
    author = ndb.StringProperty()
    permalink = ndb.StringProperty()
    subreddit = ndb.StringProperty()
    deleted = ndb.BooleanProperty(default=False)
    movies = ndb.StringProperty(repeated=True)
    post_date = ndb.DateTimeProperty()
    processed = ndb.BooleanProperty(default=False)
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
    result = urlfetch.fetch('http://www.canistream.it/services/query?movieId=%s&attributes=1&mediaType=%s' % (movie_id, movie_type))
    return json.loads(result.content)

def parse_movie_info(results):
    ret = []
    for site in results:
        name = results[site]['friendlyName']
        if results[site]['price'] > 0:
            name = "%s - %s" % (results[site]['friendlyName'], results[site]['price'])
        string = "[%s](%s)" % ( name, results[site]['url'] )
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

def get_post_key(int_id,kind):
    post_lookup = Post.query(ndb.AND(
        Post.post_kind == kind,
        Post.post_id == int_id
    )).get()
    if not post_lookup:
        return False
    else:
        return post_lookup

def is_listed(list_type,subreddit):
    if list_type is 'white':
        entity = Whitelisted
    elif list_type is 'black':
        entity = Blacklisted
    else:
        return False
    if entity:
        listed = entity.query(entity.subreddit == subreddit).get()
        if listed:
            return True
    return False


def get_movie_data(movies):
    media_types = cfg['mediatypes']
    movies_ret = []
    for imdb_id in movies:
        logging.debug("Looking up information for IMDB id: %s" %imdb_id)
        movie_obj = {}
        # Lookup IMDB name
        imdb_obj = IMDB(imdb_id)
        imdb_title = imdb_obj.get_thing('Title')
        imdb_year = imdb_obj.get_thing('Year')
        rt_tomatometer = imdb_obj.get_thing('tomatoMeter')
        if imdb_title is False:
            logging.warning("Couldn't get IMDB info for IMDB id: %s" %imdb_id)
            continue
        if imdb_obj.get_thing('Type') != "movie":
            logging.warning("%s is not a movie. Not going to proceed with this title" % imdb_title)
            continue
        # Get IMDB Rating
        imdb_rating = imdb_obj.get_thing('imdbRating')
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
                logging.debug("Going up to look up %s info for CISI movie ID: %s" % (media_type,cisi_movie_id))
                movie_obj[media_type] = get_movie_info( cisi_movie_id , media_type.lower() )
                if movie_obj[media_type]:
                    exclude = False
            if exclude:
                logging.warning("No results for all media types. Not including this movie in the list")
                movie_obj['exclude'] = True
            else:
                movie_obj['exclude'] = False
            movies_ret.append(movie_obj)
        else:
            logging.warning("No CISI results for %s with imdb_id %s" % (imdb_title,imdb_id))
    # Return Object
    return movies_ret

# Adds the post to the database
# Returns list of movies if we should comment on the post
# Returns False if we shouldn't reply to the post
def add_post_to_db(post,int_id,kind,force=False):
    movies_list = []
    should_comment = False
    permalink = None
    author = post['data']['author']
    post_date = datetime.datetime.fromtimestamp(int(post['data']['created_utc']))
    subreddit = post['data']['subreddit']
    post_lookup = get_post_key(int_id,kind)
    # If this post is not in the DB
    if not post_lookup:
        logging.info("Need to process post in the %s subreddit" % subreddit)
        list_of_movies = []
        if kind == 't3':
            # this is a post
            permalink = post['data']['permalink']
            list_of_movies = parse_text_for_imdb_ids(post['data']['selftext'])
            list_of_movies += parse_text_for_imdb_ids(post['data']['url'])
            list_of_movies += parse_text_for_imdb_ids(post['data']['title'])
        elif kind == 't1':
            # This is a comment
            permalink = post['data']['context']
            list_of_movies = parse_text_for_imdb_ids(post['data']['body'])
        movies_list = list(set(list_of_movies))
        # We want to keep a list of the movies, even if we shouldn't comment        
        post_key = Post(
            post_id = int_id,
            post_kind = kind,
            post_date = post_date,
            author = author,
            permalink = permalink,
            subreddit = subreddit,
            movies = movies_list
        ).put()
        logging.info("Finished processing post in the %s subreddit" % subreddit)
    else:
        movies_list = post_lookup.movies
    # We shouldn't comment on this post if the subreddit is not whitelisted
    # If we don't have any whitelisted subreddits, then we shouldn't comment
    if kind == 't3' and (is_listed('white',subreddit) or force is True):
            should_comment = True
    # We shouldn't comment on a summon if the subreddit is blacklisted
    # If we don't have a list of blacklisted subreddits, then we're good to comment
    elif kind == 't1' and not is_listed('black',subreddit):
        should_comment = True
    # If this user isn't on the ignore list 
    # or we shouldn't comment
    if is_author_ignored(author) or should_comment is False:
        # If we're not going to comment, then we need to mark 
        # processed as true to avoid checking this one again
        return False
    else:
        return movies_list

def comment_on_post(post, force=False):
    comment_id = None
    error_commenting = False
    if 'kind' in post:
        kind = post['kind']
    elif 'kind' in post['data']:
        kind = post['data']
    else:
        logging.error("Could not find a kind in post: %s" % post)
        return False
    int_id = int(post['data']['id'],36)
    name = post['data']['name']
    movies_list = add_post_to_db(post,int_id,kind,force)
    if movies_list is not False:
        post_key = get_post_key(int_id,kind)
        # Only continue if we haven't processed this post
        # Even if forced, we can only comment on a post once
        if post_key.processed == True:
            logging.info("We've already commented on %s before. Can not comment again" % name)
            return False
        # We should comment on this post
        movies_data = get_movie_data(movies_list)
        # If we got valid movie data back
        if movies_data:
            comment_text = format_new_post(movies_data)
            # If the comment text has info
            if comment_text is not False:
                new_post_result =  reddit.post_to_reddit(name,comment_text,'comment')
                # If the comment was posted sucessfully
                if new_post_result:
                    if not new_post_result['json']['errors']:
                        comment_id = int(new_post_result['json']['data']['things'][0]['data']['id'],36)
                        # get the name of the comment
                        comment_name = new_post_result['json']['data']['things'][0]['data']['name']
                        updated_comment_text = comment_text.format(thing_id=comment_name)
                        reddit.post_to_reddit(comment_name,updated_comment_text,'editusertext')
                    else:
                        # Set comment id to 0 and let this get put in the DB, so we don't try it again
                        logging.error("Received the following error when trying to comment: %s" % new_post_result['json']['errors'])
                else:
                    error_commenting = True
                    logging.error("Couldn't comment. Not marking this as commented in DB")
            else:
                logging.warning("No links to provide to the user for post %s" % name)
        else:
            logging.warning("No movie data was found for post %s" % name)
        if not error_commenting:
                post_key.comment_id = comment_id
                post_key.processed = True
                post_key.put()
                logging.info("Added %s to the db. Will not comment on this post again" % name)
        else:
            logging.warning("An error was encountered with %s. Not adding this post to the DB in hope a subsequent run will fix the issue" % name)
    else:
        logging.info("Reply on %s skipping." % (name))

def format_new_post(movies_data):
    default_media_types = cfg['mediatypes']
    media_types=[]
    # Check for which types have information
    # This limits it so that if we don't have
    # Information for all movies for a certain type,
    # then we won't include a blank column
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
    actual_links = False
    for index, w in enumerate(heading):
        sep = "---"
        if index > 1:
            sep+=":"
        seperator.append(sep)
    ret_line.append(" | ".join(heading))
    ret_line.append("|".join(seperator))
    excluded_movies = []
    for movie in movies_data:
        # If we have details about the movie, but no 
        # links, then add to end of the post
        if movie['exclude'] and 'imdb_title' in movie:
            logging.info("We don't have any streams, so tell the user we excluded the title")
            excluded_movies.append("[%s](%s)" % (movie['imdb_title'],movie['links']['shortUrl']))
            continue
        actual_links = True
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
    if excluded_movies:
        ret_line.append("\nNo streaming, rental, or purchase info for: "+' , '.join(excluded_movies))
    ret_line.append('\n---\n' + ' ^| '.join(['^' + a for a in SIG_LINKS]))
    # If we don't have streams for any movies, we shouldn't comment
    # Only return the formatted text if we have useful info
    if actual_links:
        return "\n".join(ret_line)
    else:
        return False

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
        else:
            # Add username to DB to be ignored
            logging.info("Adding %s to the ignore list" % author)
        ignored = True
        response =  (
            "Sorry to hear you want me to ignore you. Was it something "
            "I said? I will not reply to any posts you make in the future. "
            "If you want me to reply to your posts, you can send me "
            "[a message](%s). Also, if you "
            "wouldn't mind filling out [this survey](%s) "
            "giving me feedback, I'd really appreciate it. It would make me a better bot" %
            (REDDIT_PM_REMEMBER,REDDIT_PM_FEEDBACK)
        )
    # If subject ==  REMEMBER ME
    elif subject == "remember me":
        # Remove username from DB
        logging.info("No longer ignoring %s" % author)
        ignored = False
        response = (
            "Ok, I'll reply to your posts from now on. "
            "If you want me to stop, you can send me "
            "[a message](%s), "
            "and I'll stop replying to your posts" %
            (REDDIT_PM_IGNORE)
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

def add_to_list(message):
    author  = message['author']
    body    = message['body']
    date    = datetime.datetime.fromtimestamp(int(message['created_utc']))
    subject = message['subject'].lower()
    message_id = int(message['id'],36)
    # Get the subreddit in the message
    match = re.search(r'r/(\w+)',body)
    if not match:
        return False
    subreddit = match.group(1)
    logging.info("Subreddit is %s" % subreddit)
    # Check to see if user is moderator of subreddit
    # If not, abort now
    if reddit.is_user_moderator(subreddit,author):
        # Else, see what they want to do
        if subject == "whitelist":
            list_type = 'white'
            remove_from_entity = Blacklisted
            entity = Whitelisted
        elif subject == "blacklist":
            list_type = 'black'
            remove_from_entity = Whitelisted
            entity = Blacklisted
        if not is_listed(list_type,subreddit):
            # Subreddit is not listed
            entity(
                subreddit = subreddit,
                updated_by = author
            ).put()
            old_entity = remove_from_entity.query(remove_from_entity.subreddit==subreddit).get()
            if old_entity:
                # Delete the entity from the 
                # other list. We can't have a subreddit on both lists
                old_entity.key.delete()
            logging.info("%s is now %slisted because of %s" % (subreddit,list_type,author))
            subreddit_mods = "/r/%s" %subreddit
            reply_subject = "%s added to /u/moviesbot %s" % (subreddit_mods,subject)
            response = (
                "This message is to inform you that the request by %s "
                "to %s /r/%s has been processed. /u/moviesbot will respect "
                "this decision moving forward. You can find out more "
                "about what this means by refering to [this wiki](%s)"
                % (author,subject,subreddit,REDDIT_PM_MODS)
            )
            reddit.send_message(subreddit_mods,reply_subject,response)
    else:
        logging.warning("%s is not a moderator of %s. Abort" % (author,subreddit))
    return None

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
                response =  (
                    "Ok, I deleted my comment on your post. Sorry about that. "
                    "If you never want me to respond to you again, I understand. you can always send "
                    "[a message](%s), and I'll never "
                    "ever respond to your post, I promise. Also, if you wouldn't mind filling out "
                    "[this survey](%s) giving me feedback, "
                    "I'd really appreciate it. It would make me a better bot" %
                    (REDDIT_PM_IGNORE,REDDIT_PM_FEEDBACK)
                )
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

def search_process_reddit_posts(query,force=False):
    search_results = reddit.search_reddit(query)
    if search_results:
        for post in search_results['data']['children']:
            comment_on_post(post,force)

# Performs a search for posts with imdb links in the title,
# selftext, and url. For each post, send to comment on post
class search_imdb(webapp2.RequestHandler):
    def get(self):
        search_process_reddit_posts("title%3Aimdb.com+OR+url%3Aimdb.com+OR+imdb.com")

class search_usermention(webapp2.RequestHandler):
    def get(self):
        search_process_reddit_posts(
            "title%3A/u/{u}+OR+url%3A/u/{u}+OR+/u/{u}".format(u=cfg['reddit']['user']),
            force=True
        )

class manual_process(webapp2.RequestHandler):
    def get(self,post_id):
        post_results = reddit.api_call("https://oauth.reddit.com/comments/%s.json" % post_id)
        if post_results:
            logging.info("Forcing processing on post %s" % post_id)
            comment_on_post(post_results[0]['data']['children'][0],force=True)

# Reads unread messages from the inbox. 
class read_messages(webapp2.RequestHandler):
    def get(self):
        logging.info("Getting list of unread messages")
        # Get unread messages
        unread = reddit.get_unread_messages()
        if unread:
            logging.debug("Received the following response for unread messages %s" % unread)
            for message in unread['data']['children']:
                response = None
                author = message['data']['author']
                name = message['data']['name']
                if message['data']['was_comment']:
                    if 'subject' in message['data'] and message['data']['subject'] == "username mention":
                        subreddit = message['data']['subreddit']
                        logging.info("Got username mention in the %s subreddit" % subreddit)
                        # Check if mention was in blacklisted subreddit
                        comment_on_post(message)
                else:
                    subject = message['data']['subject'].lower()
                    logging.info("Got a message from %s with the subject %s" % (author,subject))
                    if subject in ["ignore me", "remember me"]:
                        response = ignore_message(message['data'])
                    elif subject in ["blacklist","whitelist"]:
                        response = add_to_list(message['data'])
                    elif subject == "delete":
                        response = delete_message(message['data'])
                # Mark message as read
                if reddit.mark_message_read(name):
                    if response is not None:
                        # Reply to the user
                        reply_subject = "re: %s" %subject
                        logging.info("Replying with subject: %s and response %s" % (reply_subject,response))
                        reddit.send_message(author,reply_subject,response)
        else:
            logging.error("Error getting unread messages")

class update_wiki_lists(webapp2.RequestHandler):
    def get(self):
        subreddit = cfg['subreddit']
        lists = {'white':Whitelisted,'black':Blacklisted}
        for list_type in lists:
            entity = lists[list_type]
            listed_subreddits = []
            for item in entity.query().fetch():
                listed_subreddits.append("/r/%s/" % item.subreddit)
            content = '\n\n'.join(listed_subreddits)
            page = "%slisted" % list_type
            reason = "Automated update of %slisted subreddits" % list_type
            if reddit.update_wiki(subreddit,page,content,reason):
                logging.info("Sucessfully updated the %slisted wiki in /r/%s" % (list_type,subreddit))
            else:
                logging.error("Error updating the %slisted wiki in /r/%s" % (list_type,subreddit))

application = webapp2.WSGIApplication([
    ('/tasks/search/imdb', search_imdb),
    ('/tasks/search/user', search_usermention),
    ('/tasks/manual/(\w+)', manual_process),
    ('/tasks/inbox', read_messages),
    ('/tasks/wiki', update_wiki_lists)
],
    debug=True
)
