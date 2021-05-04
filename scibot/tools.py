import logging
import json
import re
import os
import time
import datetime
import feedparser
import dateutil.parser
from os.path import expanduser
from scibot.telebot import telegram_bot_sendtext
from schedule import Scheduler

# logging parameters
logger = logging.getLogger("bot logger")
# handler determines where the logs go: stdout/file
file_handler = logging.FileHandler(f"{datetime.date.today()}_scibot.log")

logger.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)

fmt_file = (
    "%(levelname)s %(asctime)s [%(filename)s: %(funcName)s:%(lineno)d] %(message)s"
)

file_formatter = logging.Formatter(fmt_file)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


class Settings:
    """Twitter bot application settings.

    Enter the RSS feed you want to tweet, or keywords you want to retweet.
    """

    IGNORE_ERRORS = [327, 139]
    # RSS feeds to read and post tweets from.
    feed_urls = [
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1VePQbT36PBuW-0vYWywv3PuF6BRnl6iwoIY8Ud6bo2ad7LQCq/?limit=50&utm_campaign=pubmed-2&fc=20210420053033",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1HM5Uxfu7f2DxEmuq-aqm79Um6H97z55gW-utYd5e1Fq1Yngod/?limit=50&utm_campaign=pubmed-2&fc=20210420053153",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1NSu_CQNBizlmYqaPvjt8_hPOGlOnPaTChO-SFWN36pp7ZkgSs/?limit=50&utm_campaign=pubmed-2&fc=20210420053222",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1DK1DQN9MQ-BeubNAzIyke3Nq-hO8OkCvOE2oueFRGqqvy8gei/?limit=50&utm_campaign=pubmed-2&fc=20210420053342",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1DK1DQN9MQ-BeubNAzIyke3Nq-hO8OkCvOE2oueFRGqqvy8gei/?limit=50&utm_campaign=pubmed-2&fc=20210420053342",
        "http://export.arxiv.org/api/query?search_query=all:psilocybin*&start=0&max_results=100&sortBy=lastUpdatedDate&sortOrder=descending",
    ]

    pre_combined_feed = [feedparser.parse(url)["entries"] for url in feed_urls]

    # (combined_feed)

    combined_feed = [item for feed in pre_combined_feed for item in feed]
    combined_feed.sort(
        key=lambda x: dateutil.parser.parse(x["published"]), reverse=True
    )

    # Log file to save all tweeted RSS links (one URL per line).
    posted_urls_output_file = expanduser("~/drugscibot/publications.json")

    # Log file to save all retweeted tweets (one tweetid per line).
    posted_retweets_output_file = expanduser("~/drugscibot/posted-retweets.log")

    # Log file to save all retweeted tweets (one tweetid per line).
    faved_tweets_output_file = expanduser("~/drugscibot/faved-tweets.log")

    # Log file to save followers list.
    users_json_file = expanduser("~/drugscibot/users.json")

    # Include tweets with these words when retweeting.
    retweet_include_words = [
        "drugpolicy",
        "drugspolicy",
        "transformdrugspolicy",
        "transformdrugpolicy",
        "drugchecking",
        "regulatestimulants",
        "regulatedrugs",
        "sensibledrugpolicy",
        "drugpolicyreform",
        "safeconsumption",
        "harmreduction",
        "druguse",
        "safesuply",
        "safersuply",
    ]

    # Do not include tweets with these words when retweeting.
    retweet_exclude_words = [
        "sex",
        "sexual",
        "sexwork",
        "sexualwork",
        "fuck",
        "vaping",
        "vape",
        "cigarretes",
        "nicotine",
        "smoke",
        "smoking",
        "zigaretten",
    ]

    add_hashtag = [
        "psilocybin",
        "psilocybine",
        "psychedelic",
        "hallucinogenic",
        "overdose",
        "microdosing",
        "drug-policy",
        "drugspolicy",
        "mdma",
        "drugpolicy",
        "drug policy",
        "ayahuasca",
        "psychopharmacology",
        "neurogenesis",
        "5-meo-dmt",
        "serotonergic",
        "ketamine",
        "psychotherapy",
        "harm reduction",
        "methadone",
    ]  # trip

    watch_add_hashtag = [
        "cocaina",
        "cocaine",
        "alzheimer",
        "depression",
        "anxiety",
        "droga",
        "coca",
        "dmt",
        "lsd",
        "therapy",
        "psychiatry",
        "mentalhealth",
        "trip",
        "mental health",
        "clinical trial",
        "consciousness",
        "drug",
        "meta-analysis",
        "dopamine",
        "serotonin",
        "psychological",
        "metaanalysis",
        "reform",
    ]

    # list of the distribution
    mylist_id = "1306244304000749569"


class SafeScheduler(Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.
    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.
    """

    def __init__(self, reschedule_on_failure=True):
        """
        If reschedule_on_failure is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        super().__init__()

    def _run_job(self, job):
        try:
            super()._run_job(job)

        except Exception as e:
            logger.exception(e)
            telegram_bot_sendtext(f"[Job Error] {e}")
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()


def shorten_text(text: str, maxlength: int) -> str:
    """Truncate text and append three dots (...) at the end if length exceeds
    maxlength chars.

    Parameters
    ----------
    text: str
        The text you want to shorten.
    maxlength: int
        The maximum character length of the text string.

    Returns
    -------
    str
        Returns a shortened text string.
    """
    return (text[:maxlength] + "...") if len(text) > maxlength else text


def insert_hashtag(title: str):

    for x in Settings.add_hashtag:
        if re.search(fr"\b{x}", title.lower()):
            pos = (re.search(fr"\b{x}", title.lower())).start()
            if " " in x:
                title = title[:pos] + "#" + title[pos:].replace(" ", "", 1)
            else:
                title = title[:pos] + "#" + title[pos:]
    return title


def compose_message(item: feedparser.FeedParserDict) -> str:
    """Compose a tweet from an RSS item (title, link, description)
    and return final tweet message.

    Parameters
    ----------
    item: feedparser.FeedParserDict
        An RSS item.

    Returns
    -------
    str
        Returns a message suited for a Twitter status update.
    """
    title = insert_hashtag(item["title"])

    message = shorten_text(title, maxlength=250) + " 1/5  " + item["link"]
    return message


def is_in_logfile(content: str, filename: str) -> bool:
    """Does the content exist on any line in the log file?

    Parameters
    ----------
    content: str
        Content to search file for.
    filename: str
        Full path to file to search.

    Returns
    -------
    bool
        Returns `True` if content is found in file, otherwise `False`.
    """
    if os.path.isfile(filename):
        with open(filename, "r") as jsonFile:
            article_log = json.load(jsonFile)
        if content in article_log:
            return True
    return False


def write_to_logfile(content: dict, filename: str):
    """Append content to json file.

    Parameters
    ----------
    content: dic
        Content to append to file.
    filename: str
        Full path to file that should be appended.
    """
    try:
        with open(filename, "w") as fp:
            json.dump(content, fp)
    except IOError as e:
        logger.exception(e)


def shorten_text(text: str, maxlength: int) -> str:
    """Truncate text and append three dots (...) at the end if length exceeds
    maxlength chars.

    Parameters
    ----------
    text: str
        The text you want to shorten.
    maxlength: int
        The maximum character length of the text string.

    Returns
    -------
    str
        Returns a shortened text string.
    """
    return (text[:maxlength] + "...") if len(text) > maxlength else text


def scheduled_job(read_rss_and_tweet, retweet_own, search_and_retweet):
    schedule = SafeScheduler()
    # job 1
    schedule.every().day.at("22:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("06:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("14:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    # job 2
    schedule.every().day.at("01:10").do(retweet_own)
    schedule.every().day.at("09:10").do(retweet_own)
    schedule.every().day.at("17:10").do(retweet_own)
    # job 3
    schedule.every().day.at("00:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("03:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("06:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("09:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("12:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("15:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("18:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("21:20").do(search_and_retweet, "global_search")

    schedule.every().day.at("01:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("04:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("07:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("10:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("13:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("16:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("19:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("22:25").do(search_and_retweet, "list_search")
    # job love
    schedule.every(30).minutes.do(search_and_retweet, "give_love")

    while 1:
        schedule.run_pending()
        time.sleep(1)
