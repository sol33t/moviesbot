import urllib
import base64
import json
import time
import logging
import config
from google.appengine.api import urlfetch
from google.appengine.api.urlfetch_errors import *
from google.appengine import runtime

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
                logging.error("Error inilitizing with Reddit and user %s" % config.reddit['user'])
        else:
            logging.error("Could not get auth token")

    def get_token(self):
        base64creds = base64.b64encode(config.reddit['client_id'] + ":" + config.reddit['client_secret'])
        request_payload = {"grant_type": "password",
            "duration": "permanent",
            "username": config.reddit['user'],
            "password": config.reddit['password']
        }
        request_payload_encoded = urllib.urlencode(request_payload)
        headers={
            "Authorization": "Basic %s" % base64creds,
            "User-Agent": "moviesbot version 0.0.1 by /u/moviesbot"
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


    def api_call(self,url,payload=None,recursive=True):
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
        logging.info("Making Reddit API call to the following URL: %s" % url)
        try:
            result = urlfetch.fetch(url, method=method, payload=payload, headers=headers)
        except (runtime.DeadlineExceededError, urlfetch.ConnectionClosedError) as e:
            if recursive:
                logging.info("Got error: %s. Retrying request in 2 seconds" % e)
                time.sleep(2)
                return self.api_call(url,payload,recursive=False)
            else:
                logging.warning("Connection closed during retry. Aborting this API call")
                return False
        if result.status_code == 200:
            logging.debug(result.content)
            return json.loads(result.content)
        elif result.status_code == 401:
            logging.info("Looks like the token expired. Getting new token")
            # Get a new token here
            # Call the api call function again
            if self.get_token() and recursive:
                 return self.api_call(url,payload,recursive=False)
            else:
                logging.error("Unauthorized error after renewing auth token")
                return False
        elif result.status_code == 429:
            logging.info("HTTP 429 error. Retrying request in 2 seconds")
            time.sleep(2)
            if recursive:
                return self.api_call(url,payload,recursive=False)
            else:
                logging.warning("Still getting 429 error after sleeping")
                return False
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
        logging.info("Performing search on Reddit for: %s" % query)
        return self.api_call (url)

    def post_to_reddit(self,thing_id,text,post_type='comment'):
        logging.info("Posting comment to reddit post %s" % thing_id)
        logging.debug("Text is %s" % text)
        url = "https://oauth.reddit.com/api/%s/.json" % post_type
        payload = { 'thing_id':thing_id,
                    'text':text.encode('utf-8'),
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
