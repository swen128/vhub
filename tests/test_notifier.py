import boto3
import pytest
from moto import mock_dynamodb2
from vhub.notifier import main
from vhub.utils import read_json


@pytest.fixture
def table():
    with mock_dynamodb2():
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

        table.put_item(Item={
            "name": "test_channel_0",
            "url": "https://www.youtube.com/channel/test_channel_0"
        })
        table.put_item(Item={
            "name": "test_channel_1",
            "url": "https://www.youtube.com/channel/test_channel_1"
        })

        yield table


def test_found(table):
    event = read_json("tests/aws_event/dynamodb/Videos/with_mention.json")
    video, channels = main(event, table)

    channel_names = set(channel.name for channel in channels)
    
    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_video"
    assert channel_names == {"test_channel_0", "test_channel_1"}


def test_host_not_found(table):
    event = read_json("tests/aws_event/dynamodb/Videos/unknown_host.json")
    video, channels = main(event, table)

    assert len(channels) == 1


def test_mention_not_found(table):
    event = read_json("tests/aws_event/dynamodb/Videos/unknown_mention.json")
    video, channels = main(event, table)

    assert len(channels) == 1


def test_none_found(table):
    event = read_json("tests/aws_event/dynamodb/Videos/unknown_host_no_mention.json")
    video, channels = main(event, table)

    assert len(channels) == 0