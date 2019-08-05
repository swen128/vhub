import logging
import os
from typing import Iterable, Optional, Tuple, Set

import boto3
import tweepy
from boto3.dynamodb.types import TypeDeserializer
from boto3_type_annotations import dynamodb
from toolz import valmap
from twitter_text import parse_tweet

from .youtube import YoutubeVideo, YoutubeChannel, short_youtube_video_url, mentioned_channel_urls

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def vtuber_channel_detail(url: str, table: dynamodb.Table) -> Optional[YoutubeChannel]:
    response = table.get_item(Key={'url': url})
    dic = response.get('Item')

    if dic is None:
        return None
    else:
        return YoutubeChannel(
            url=dic['url'],
            name=dic['name'],
            is_host_blacklisted=dic.get('is_host_blacklisted'),
            is_guest_blacklisted=dic.get('is_guest_blacklisted')
        )


def mentioned_vtuber_channels(video: YoutubeVideo, table: dynamodb.Table) -> Iterable[YoutubeChannel]:
    channels = mentioned_channel_urls(video)
    details = (vtuber_channel_detail(channel, table) for channel in channels)
    vtuber_channels = (x for x in details if x is not None and not x.is_guest_blacklisted)

    return vtuber_channels


def video_from_event(event) -> YoutubeVideo:
    image = event['Records'][0]['dynamodb']['NewImage']
    dic = valmap(TypeDeserializer().deserialize, image)

    return YoutubeVideo(**dic)


def is_valid_tweet(text: str) -> bool:
    return parse_tweet(text).valid


def message(video: YoutubeVideo, channel_names: Iterable[str]) -> str:
    url = short_youtube_video_url(video.url)
    channel_names_lines = '\n'.join(sorted(channel_names))

    mes_short = f"#VTuberコラボ通知\n{url}"
    mes_mid = f"#VTuberコラボ通知\n{video.title}\n{url}"
    mes_long = f"{mes_short}\n\n【参加者】\n{channel_names_lines}"
    mes_max = f"{mes_mid}\n\n【参加者】\n{channel_names_lines}"
    messages = [mes_max, mes_long, mes_mid, mes_short]

    return next(filter(is_valid_tweet, messages))


def main(event, table: dynamodb.Table, twitter: tweepy.API):
    video = video_from_event(event)
    host_channel = vtuber_channel_detail(video.channel_url, table)
    mentioned_channels = list(mentioned_vtuber_channels(video, table))

    if host_channel is None:
        channels = mentioned_channels
    elif host_channel.is_host_blacklisted:
        channels = []
    else:
        channels = [host_channel] + mentioned_channels

    channel_names = set(channel.name for channel in channels)

    if len(channel_names) >= 2:
        mes = message(video, channel_names)
        twitter.update_status(mes)


def lambda_handler_prod(event, context):
    try:
        CK = os.environ['TWITTER_CONSUMER_KEY']
        CS = os.environ['TWITTER_CONSUMER_SECRET']
        AT = os.environ['TWITTER_ACCESS_TOKEN']
        AS = os.environ['TWITTER_ACCESS_SECRET']
        auth = tweepy.OAuthHandler(CK, CS)
        auth.set_access_token(AT, AS)
        twitter = tweepy.API(auth)

        table_name = os.environ["CHANNELS_TABLE"]
        table = boto3.resource('dynamodb').Table(table_name)

        main(event, table, twitter)
    except Exception as e:
        logger.error('An unexpected error happened.')
        logger.exception(e)


def lambda_handler_dev(event, context):
    class MockTwitter:
        @staticmethod
        def update_status(message: str):
            logger.info(message)

    try:
        twitter = MockTwitter()

        table_name = os.environ["CHANNELS_TABLE"]
        table = boto3.resource('dynamodb').Table(table_name)

        main(event, table, twitter)
    except Exception as e:
        logger.error('An unexpected error happened.')
        logger.exception(e)
