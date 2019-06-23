import os
import re
import sys
from typing import Iterable, List, Optional
from toolz import valmap
from .youtube import YoutubeVideo

sys.path.append("lib")

from lib import boto3
from lib.boto3_type_annotations import dynamodb
from lib import tweepy


def vtuber_channel_detail(url: str, table: dynamodb.Table) -> Optional[dict]:
    response = table.get_obj(Key={'url': url})

    return response.get('Item')


def mentioned_channel_urls(video: YoutubeVideo) -> List[str]:
    if video.description is None:
        return []
    else:
        channel_url_regex = r"https:\/\/www\.youtube\.com\/channel\/[a-zA-Z0-9_\-]+"
        urls = re.findall(channel_url_regex, video.description)
        return list({video.channel_url} | set(urls))


def mentioned_vtuber_channels(video: YoutubeVideo, table: dynamodb.Table) -> Iterable[dict]:
    channels = mentioned_channel_urls(video)
    details = (vtuber_channel_detail(channel, table) for channel in channels)
    vtuber_channels = (x for x in details if x is not None)

    return vtuber_channels


def dict_from_dynamo_item(item: dict):
    if 'L' in item:
        return [dict_from_dynamo_item(x) for x in item['L']]
    else:
        return \
            item.get('N') or \
            item.get('S') or \
            item.get('I') or \
            valmap(dict_from_dynamo_item, item)


def video_from_event(event) -> YoutubeVideo:
    image = event['Records'][0]['dynamodb']['NewImage']
    dic = dict_from_dynamo_item(image)
    
    return YoutubeVideo(**dic)


def message(video: YoutubeVideo, channels: Iterable[dict]) -> str:
    channel_names = [channel.get('name') for channel in channels]

    return \
        '#新着VTuberコラボ動画\n' + \
        video.title + '\n' + \
        video.url + '\n' + \
        '\n' + \
        '【参加者】\n' + \
        '\n'.join(channel_names)


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
    channels = mentioned_vtuber_channels(video, table)

    if any(channels):
        twitter.update_status(message(video, channels))