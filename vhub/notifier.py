import os
import re
import sys
import boto3
import logging
from boto3.dynamodb.types import TypeDeserializer
from typing import Iterable, List, Optional
from .youtube import YoutubeVideo, short_youtube_video_url

sys.path.append("lib")

from lib.boto3_type_annotations import dynamodb
from lib import tweepy
from lib.toolz import valmap, get


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def vtuber_channel_detail(url: str, table: dynamodb.Table) -> Optional[dict]:
    response = table.get_item(Key={'url': url})

    return response.get('Item')


def mentioned_channel_urls(video: YoutubeVideo) -> List[str]:
    if video.description is None:
        return []
    else:
        channel_url_regex = r"https:\/\/www\.youtube\.com\/channel\/[a-zA-Z0-9_\-]+"
        urls = re.findall(channel_url_regex, video.description)
        return list(set(urls) - {video.channel_url})


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


def tweet(messages: Iterable[str], twitter: tweepy.API):
    for message in messages:
        try:
            twitter.update_status(message)
            logger.info('Tweeted: %s', message)
            return
        except tweepy.TweepError as e:
            if e.api_code == 186:
                continue
            elif e.api_code == 187:
                logger.warn('Attempted tweet is a duplicate and thus skipped: %s', message)
                return
            else:
                logger.exception('Failed to tweet: %s')
                return
        except:
            logger.exception('Failed to tweet: %s')
            return


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
