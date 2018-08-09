import praw
from od_database.reddit_bot import RedditBot
import re
import os
import json
from od_db_client import OdDatabase
from od_database.od_util import get_top_directory, is_od, is_valid_url
import shlex
import config


PATTERN = re.compile("[\[\]\\\()]+")
od_db_client = OdDatabase(config.API_URL, config.API_KEY)


def process_comment(comment, bot):

    text = PATTERN.sub(" ", comment.body).strip()

    if text.startswith("u/opendirectories-bot") or text.startswith("/u/opendirectories-bot"):
        lines = shlex.split(text,)
        if len(lines) > 1:
            text = lines[1]
            if text.startswith("?"):
                process_query(comment, bot, text[1:])
            else:
                process_url(comment, bot, text)


def process_query(comment, bot, query):

    print("Search query '" + query + "'")

    hits = od_db_client.search(
        query, 0, 10,
        "score", [],
        0, 0,
        False, ["path", "name^5", "name.nGram^2"],
        0, 0
    )
    message = od_db_client.format_search_hits(hits, query) + "\n***    \n" + bot.bottom_line
    print(message)
    bot.reply(comment, message)


def process_url(comment, bot, url):

    url = os.path.join(url, "")  # Add trailing slash

    if not is_valid_url(url):
        print("Url is invalid")
        handle_invalid_url(comment, bot, url)
        return

    if od_db_client.website_is_blacklisted(url):
        print("Website is blacklisted")
        handle_blacklisted(comment, bot)
        return

    url = get_top_directory(url)
    website_id = od_db_client.website_by_url(url)

    if not website_id:
        print("Website does not exist")

        if not is_od(url):
            print("Website is not an od")
            handle_non_od_website(comment, bot, url)
            return

        handle_new_website(comment, bot, url)
    else:
        print("Website already exists")
        handle_existing_website(comment, bot, website_id)


def handle_invalid_url(comment, bot, url):
    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you provided: `" +
              url + "` is not valid. Make sure that you include the `http(s)://` prefix.    \n***    \n" + bot.bottom_line)


def handle_blacklisted(comment, bot):
    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately my programmer has blacklisted this website."
                       " If you think that this is an error, please "
                       "[contact him](https://old.reddit.com/message/compose?to=Hexahedr_n)    \n***    \n" + bot.bottom_line)


def handle_non_od_website(comment, bot, url):
    bot.reply(comment, "Hello, " + str(comment.author) + ". Unfortunately it seems that the link you provided: `" +
              url + "` does not point to an open directory. This could also mean that the website is not responding "
                    "(in which case, feel free to retry in a few minutes). If you think that this is an error, please "
                    "[contact my programmer](https://old.reddit.com/message/compose?to=Hexahedr_n)    \n***    \n" +
              bot.bottom_line)


def handle_new_website(comment, bot, url):

    website_id = od_db_client.add_website(url)
    if website_id:
        reply = bot.reply(comment, "Hello, " + str(comment.author) + ". This website was added to od-database and will "
                                   "be processed as soon as a crawl server is available. Thank you for your "
                                   "contribution to the database!    \nI will edit this comment when the website has"
                                   " been crawled and indexed. Website id is `" + str(website_id) + "`.    \n***    \n"
                                   + bot.bottom_line)

        od_db_client.enqueue(website_id=website_id, url=url, priority=2, callback_type="reddit_comment",
                             callback_args=json.dumps({
                                 "comment_id": reply.id
                             }))
    else:
        print("Could not create new website")


def handle_existing_website(comment, bot, website_id):

    stats = od_db_client.get_stats(website_id)
    message_header = "Hello, " + str(comment.author) + ". This website was crawled and indexed by od-database at `" + \
                     stats["report_time"] + "`. "

    message = bot.get_comment(stats, website_id, message_header)
    print(message)
    bot.reply(comment, message)


def process_post(submission):
    print("Checking new post with url " + submission.url)
    url = os.path.join(submission.url, "")

    if not is_valid_url(url):
        print("Url is invalid")
        return

    if od_db_client.website_is_blacklisted(url):
        print("Website is blacklisted")
        return

    url = get_top_directory(url)
    website_id = od_db_client.website_by_url(url)

    if not website_id:
        print("Website does not exist")

        if not is_od(url):
            print("Website is not an od")
            return

        handle_new_website(submission, bot, url)
    else:
        print("Website already exists")
        handle_existing_website(submission, bot, website_id)


if __name__ == "__main__":
    reddit = praw.Reddit('opendirectories-bot',
                         user_agent='github.com/simon987/opendirectories-bot-new (by /u/Hexahedr_n)')
    bot = RedditBot("processed.txt", reddit)
    subreddit = reddit.subreddit("test")

    # Check comments
    for comment in subreddit.comments(limit=50):
        if not bot.has_crawled(comment):
            process_comment(comment, bot)

    # Check submissions
    for submission in subreddit.new(limit=3):
        if not submission.is_self and not bot.has_crawled(submission):
            process_post(submission)


