import urllib
import base64
import json
import time
import logging
import config
from google.appengine.api import urlfetch

class MediaHound:

    def __init__(self):
        if self.get_token() is not True:
            logging.error("Could not get MediaHound auth token")
            raise Exception("Can not proceed without valid MediaHound Auth token")

    def get_token(self):
        base64creds = base64.b64encode(config.mediahound['client_id'] + ":" + config.mediahound['client_secret'])
        request_payload = { "grant_type": "client_credentials" }
        request_payload_encoded = urllib.urlencode(request_payload)
        headers={
            "Authorization": "Basic %s" % base64creds,
            "User-Agent": "moviesbot version 0.0.1 by /u/moviesbot"
        }
        result = urlfetch.fetch("https://api.mediahound.com/1.2/security/oauth/token",
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
                logging.info("Setting mediahound auth token")
                self.auth_token = auth_token["access_token"]
                self.auth_expires = int(time.time())+auth_token['expires_in']
                logging.debug("Auth token is %s and expires at %s" % (self.auth_token,self.auth_expires))
                return True
        else:
            logging.error("Got the following status code: %s" % result.status_code)
            self.auth_token = False
            return False

    def graph_enter(self,raw_ids):
        # Take the raw_ids and make into URL Format
        logging.debug(raw_ids)
        ids = '&'.join(['ids={0}'.format(i) for i in raw_ids])
        base_url = "https://api.mediahound.com/1.2/graph/enter/raw?%s" % ids
        logging.debug("Going to request graph media from the following address: %s" % base_url)
        result = urlfetch.fetch(
            url="%s&access_token=%s" % (base_url, self.auth_token)
        )
        if result.status_code == 200:
            json_ret = json.loads(result.content)
            return json_ret['values']
        else:
            logging.error("The MediaHound call returned with status code %d" % result.status_code)
            return None
    
    def graph_media(self, mhid, media_type='metadata'):
        base_url = "https://api.mediahound.com/1.2/graph/media/%s" % mhid
        params = ["access_token=%s" % self.auth_token]
        if media_type == 'sources':
            base_url += "/sources"
        params_string = '&'.join(params)
        logging.debug("Going to request graph media from the following address: %s" % base_url)
        result = urlfetch.fetch(
            url="%s?%s" % (base_url,params_string)
        )
        if result.status_code == 200:
            logging.debug("Successfully got mediahound graph media. Returning contents")
            json_ret = json.loads(result.content)
            return json_ret
        else:
            logging.error("The MediaHound call returned with status code %d" % result.status_code)
            return None
