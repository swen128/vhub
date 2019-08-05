from typing import Tuple, List

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

    assert twitter.tweeted_messages == expected
