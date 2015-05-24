import json
import config
from google.appengine.api import urlfetch

def get_imgur_album_images(album_id):
    headers = {"Authorization": "Client-ID "+ config.imgur['client_id']}
    result = urlfetch.fetch("https://api.imgur.com/3/album/%s/images" % album_id, headers=headers)
    return json.loads(result.content)