import logging
import os
from typing import Iterable

import boto3
import requests
from boto3_type_annotations import dynamodb
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
import re
from toolz import assoc, groupby

from vhub.utils import emptystr_to_none
from vhub.youtube import YoutubeChannel

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_channels_with_multiple_affiliations(channels: Iterable[YoutubeChannel]) -> Iterable[YoutubeChannel]:
    groups = groupby(key=lambda x: x.url, seq=channels)

    for group in groups.values():
        affiliations = [channel.affiliations[0] for channel in group]
        channel = group[0]
        dic = assoc(vars(channel), 'affiliations', affiliations)

        yield YoutubeChannel(**dic)


def _parse_vtubers_list(html: str) -> Iterable[YoutubeChannel]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except:
        soup = BeautifulSoup(html, "html5lib")

    channels = soup.select("div#main-area div.channel ul.icon li:not(.empty)")

    category = None  # This is mutated inside the `for` statement below.

    for channel in channels:
        category_elem = channel.select_one("h3")

        if category_elem:
            category = category_elem.get("id")
        else:
            thumbnail = channel.select_one("p.thumbnail a img")
            a = channel.select_one("p.channelName a")
            href = a.get("href")

            channel_id = re.fullmatch(r"\/channel\/\?id=(.+)", href).group(1)

            yield YoutubeChannel(
                url=f"https://www.youtube.com/channel/{channel_id}",
                name=a.text,
                thumbnail=thumbnail.get("src"),
                affiliations=[category]
            )


def parse_vtubers_list(html: str) -> Iterable[YoutubeChannel]:
    """
    Parse the web page: https://vtuber-antenna.net/list/
    """
    return process_channels_with_multiple_affiliations(_parse_vtubers_list(html))


def save_channel(table: dynamodb.Table, channel: YoutubeChannel):
    try:
        table.update_item(
            Key={'url': channel.url},
            AttributeUpdates={
                'name': {'Value': channel.name, 'Action': 'PUT'},
                'thumbnail': {'Value': channel.thumbnail, 'Action': 'PUT'},
                'affiliations': {'Value': channel.affiliations, 'Action': 'PUT'}
            }
        )
        logger.info('Successfully saved a YouTube channel: %s', channel.url)
    except ClientError as e:
        logger.error('Failed to save a YouTube channel: %s', channel.url)
        logger.exception('The reason being: %s', e)


def main(response: requests.Response, table: dynamodb.Table):
    if response.ok:
        channels = parse_vtubers_list(response.text)

        for channel in channels:
            save_channel(table, channel)
    else:
        logger.warning("The request to '%s' failed with the status code `%s`.",
                       response.url, response.status_code)
        logger.warning(response.text)


def lambda_handler(event, context):
    table_name = os.environ['CHANNELS_TABLE']
    table = boto3.resource("dynamodb").Table(table_name)

    url = "https://vtuber-antenna.net/list/"
    response = requests.get(url)

    main(response, table)
