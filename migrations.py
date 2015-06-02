import webapp2
import logging
import datetime
from modules.reddit import Reddit
from google.appengine.ext import ndb

class Post(ndb.Model):
    post_id = ndb.IntegerProperty()
    post_kind = ndb.StringProperty()
    comment_id = ndb.IntegerProperty()
    name = ndb.StringProperty(indexed=True)
    author = ndb.StringProperty()
    permalink = ndb.StringProperty()
    subreddit = ndb.StringProperty()
    movies = ndb.StringProperty(repeated=True)
    post_date = ndb.DateTimeProperty()
    processing = ndb.BooleanProperty(default=False)
    deleted = ndb.BooleanProperty()
    commented = ndb.BooleanProperty(default=False)
    added = ndb.DateTimeProperty(auto_now_add=True)
    reply_date = ndb.DateTimeProperty()

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

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
    return ((num == 0) and numerals[0]) or (baseN(num // b, b, numerals).lstrip(numerals[0]) + numerals[num % b])

def add_comment(post_key,name,deleted):
    logging.info("Adding comment %s" % name)
    comment_key  = Comment(
        id       = name,
        parent   = post_key,
        name     = name,
        deleted  = deleted,
        revision = 0
    ).put()
    post_results = reddit.api_call("https://oauth.reddit.com/api/info.json?id=%s" % name)
    if post_results:
        comment = comment_key.get()
        logging.info("Processing for post: %s" % name)
        post = post_results['data']['children'][0]
        updated = datetime.datetime.fromtimestamp(int(post['data']['created_utc']))
        comment.updated = updated
        comment.score = post['data']['score']
        comment.put()
        body = post['data']['body']
        comment_rev_key = CommentRevisions(
            id = '0',
            parent = comment_key,
            body = body,
            reply_date = updated
        ).put()

reddit = Reddit()

class update_db(webapp2.RequestHandler):
    def get(self):
        posts = Post.query(
            Post.post_id > 0
        )
        for post in posts:
            post_key = post.key
            post_name = "%s_%s" % (post.post_kind,baseN(post.post_id,36))
            logging.info(post_name)
            logging.debug(post)
            logging.debug(post.comment_id)
            commented = False
            if post.comment_id > 0:
                commented = True
            new_post = Post(
                id        = post_name,
                name      = post_name,
                post_kind = post.post_kind,
                movies    = post.movies,
                post_date = post.post_date,
                author    = post.author,
                permalink = post.permalink,
                subreddit = post.subreddit,
                added     = post.reply_date,
                commented = commented,
            )
            if commented is True:
                if type(post.comment_id) is list:
                    logging.info("Comment is a list. Need to create several new comments")
                    for comment_id in post.comment_id:
                        if comment_id:
                            comment_name = "t1_%s" % baseN(comment_id,36)
                            add_comment(ndb.Key(Post, post_name),comment_name,post.deleted)
                else:
                    logging.info("Comment is not a list")
                    comment_name = "t1_%s" % baseN(post.comment_id,36)
                    add_comment(ndb.Key(Post, post_name),comment_name,post.deleted)
            # Delete the old key
            post.key.delete()
            new_post.put()

application = webapp2.WSGIApplication([
    ('/migrations/update_db', update_db)
],
    debug=True
)