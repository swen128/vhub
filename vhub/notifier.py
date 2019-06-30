import os
import sys
import boto3
import logging
from boto3.dynamodb.types import TypeDeserializer
from typing import Iterable, Optional
from .youtube import YoutubeVideo, short_youtube_video_url, mentioned_channel_urls

sys.path.append("lib")

from lib.boto3_type_annotations import dynamodb
from lib import tweepy
from lib.toolz import valmap, get


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def vtuber_channel_detail(url: str, table: dynamodb.Table) -> Optional[dict]:
    response = table.get_item(Key={'url': url})

    return response.get('Item')


def mentioned_vtuber_channels(video: YoutubeVideo, table: dynamodb.Table) -> Iterable[dict]:
    channels = mentioned_channel_urls(video)
    details = (vtuber_channel_detail(channel, table) for channel in channels)
    vtuber_channels = (x for x in details if x is not None)

    return vtuber_channels


def video_from_event(event) -> YoutubeVideo:
    image = event['Records'][0]['dynamodb']['NewImage']
    dic = valmap(TypeDeserializer().deserialize, image)
    
    return YoutubeVideo(**dic)


def message(video: YoutubeVideo, channels: Iterable[dict]) -> str:
    url = short_youtube_video_url(video.url)
    channel_names = [channel.get('name') for channel in channels]
    channel_names_lines = '\n'.join(channel_names)

    mes_short = f"#VTuberコラボ通知\n{url}"
    mes_mid = f"#VTuberコラボ通知\n{video.title}\n{url}"
    mes_long = f"{mes_short}\n\n【参加者】\n{channel_names_lines}"
    mes_max = f"{mes_mid}\n\n【参加者】\n{channel_names_lines}"
    
    return [mes_max, mes_long, mes_mid, mes_short]


def tweet_(message: str, twitter: tweepy.API):
    """
    Try to tweet a single `message` and log the result.
    Raises a `ValueError` iff `message` is too long to tweet.
    """
    try:
        twitter.update_status(message)
        logger.info('Tweeted: %s', message)
    except tweepy.TweepError as e:
        if e.api_code == 186:
            raise ValueError("The message is too long to tweet.")
        else:
            logger.error('Failed to tweet: %s', message)
            logger.exception('The reason being: %s', e)
    except Exception as e:
        logger.error('Failed to tweet: %s', message)
        logger.exception('The reason being: %s', e)


def tweet(messages: Iterable[str], twitter: tweepy.API):
    """
    Tweet the first message in `messages` having an appropriate length.
    `messages` are assumed to be sorted by length in descending order.
    """
    for message in messages:
        try:
            tweet_(message, twitter)
            return
        except ValueError:
            pass


def lambda_handler(event, context):
    CK = os.environ['TWITTER_CONSUMER_KEY']
    CS = os.environ['TWITTER_CONSUMER_SECRET']
    AT = os.environ['TWITTER_ACCESS_TOKEN']
    AS = os.environ['TWITTER_ACCESS_SECRET']
    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, AS)
    twitter = tweepy.API(auth)

    db = boto3.resource('dynamodb')
    table = db.Table('Channels')

    video = video_from_event(event)
    host_channel = vtuber_channel_detail(video.channel_url, table)
    mentioned_channels = list(mentioned_vtuber_channels(video, table))

    if host_channel is not None and any(mentioned_channels):
        channels = [host_channel] + mentioned_channels
        messages = message(video, channels)

        tweet(messages, twitter)
