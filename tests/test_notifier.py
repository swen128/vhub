import re
from dataclasses import dataclass
from typing import Tuple, List, Optional, Iterable

import boto3
import pytest
from moto import mock_dynamodb2
from twitter_text import parse_tweet

from vhub.notifier import main
from vhub.utils import read_yaml


class MockTwitter:
    def __init__(self):
        self.tweeted_messages = []

    def update_status(self, text: str):
        if parse_tweet(text).valid:
            self.tweeted_messages.append(text)
        else:
            raise ValueError(f'The tweet text is invalid: {text}')


@dataclass(frozen=True)
class NotificationTweet:
    url: str
    title: Optional[str]
    channels: Iterable[str]

    def __eq__(self, other):
        return \
            self.url == other.url and \
            self.title == other.title and \
            set(self.channels) == set(other.channels)


def parse_notification_tweet(text: str) -> NotificationTweet:
    try:
        parts = text.split('\n\n【参加者】\n')

        if len(parts) == 1:
            [video_info] = parts
            channels = None
        elif len(parts) == 2:
            video_info, channels = parts
        else:
            raise AssertionError()

        pattern = re.compile(
            r'#VTuberコラボ通知\n'
            r'(?:(?P<title>.+)\n)?'
            r'(?P<url>https://youtu\.be/.+)'
        )
        match = pattern.fullmatch(video_info)

        return NotificationTweet(
            url=match.group('url'),
            title=match.group('title'),
            channels=[] if channels is None else channels.splitlines()
        )
    except:
        raise AssertionError(f"Invalid tweet message: {text}")


def get_table(test_cases: dict) -> Tuple[str, List[list]]:
    header = ",".join(test_cases[0].keys())
    values = [list(case.values()) for case in test_cases]
    return header, values


test_cases = read_yaml('tests/cases/notifier.yml')


@pytest.mark.parametrize(*get_table(test_cases))
@mock_dynamodb2
def test_notifier(description: str, event: List[dict], channels: List[dict], expected: List[dict]):
    twitter = MockTwitter()

    db = boto3.resource('dynamodb', region_name='us-east-2')
    db.create_table(
        TableName='Channels',
        KeySchema=[
            {
                'AttributeName': 'url',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'url',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    table = db.Table('Channels')

    for channel in channels:
        table.put_item(Item=channel)

    main(event, table, twitter)

    for message, truth in zip(twitter.tweeted_messages, expected):
        assert parse_notification_tweet(message) == NotificationTweet(**truth)
