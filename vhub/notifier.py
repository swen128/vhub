import boto3
import logging
import os
import tweepy
from boto3.dynamodb.types import TypeDeserializer
from boto3_type_annotations import dynamodb
from toolz import valmap, get
from typing import Iterable, Optional, Tuple, List
from .youtube import YoutubeVideo, YoutubeChannel, short_youtube_video_url, mentioned_channel_urls


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def vtuber_channel_detail(url: str, table: dynamodb.Table) -> Optional[YoutubeChannel]:
    response = table.get_item(Key={'url': url})
    dic = response.get('Item')

    if dic is None:
        return None
    else:
        return YoutubeChannel(url=dic['url'], name=dic['name'])


def mentioned_vtuber_channels(video: YoutubeVideo, table: dynamodb.Table) -> Iterable[dict]:
    channels = mentioned_channel_urls(video)
    details = (vtuber_channel_detail(channel, table) for channel in channels)
    vtuber_channels = (x for x in details if x is not None)

    return vtuber_channels


def video_from_event(event) -> YoutubeVideo:
    image = event['Records'][0]['dynamodb']['NewImage']
    dic = valmap(TypeDeserializer().deserialize, image)
    
    return YoutubeVideo(**dic)


def message(video: YoutubeVideo, channels: Iterable[YoutubeChannel]) -> Iterable[str]:
    url = short_youtube_video_url(video.url)
    channel_names = [channel.name for channel in channels]
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


def main(event, table: dynamodb.Table) -> Optional[Tuple[YoutubeVideo, List[YoutubeChannel]]]:
    video = video_from_event(event)
    host_channel = vtuber_channel_detail(video.channel_url, table)
    mentioned_channels = list(mentioned_vtuber_channels(video, table))

    if host_channel is None:
        channels = mentioned_channels
    else:
        channels = [host_channel] + mentioned_channels

    return (video, channels)


def lambda_handler_prod(event, context):
    CK = os.environ['TWITTER_CONSUMER_KEY']
    CS = os.environ['TWITTER_CONSUMER_SECRET']
    AT = os.environ['TWITTER_ACCESS_TOKEN']
    AS = os.environ['TWITTER_ACCESS_SECRET']
    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, AS)
    twitter = tweepy.API(auth)

    table_name = os.environ["CHANNELS_TABLE"]
    table = boto3.resource('dynamodb').Table(table_name)

    video, channels = main(event, table)

    if len(channels) >= 2:
        messages = message(video, channels)
        tweet(messages, twitter)


def lambda_handler_dev(event, context):
    table_name = os.environ["CHANNELS_TABLE"]
    table = boto3.resource('dynamodb').Table(table_name)

    video, channels = main(event, table)
    messages = message(video, channels)

    logger.info(messages[0])