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
            "url": "https://www.youtube.com/channel/Av87muUsEdf7amViaQ4L84"
        })
        table.put_item(Item={
            "name": "test_channel_1",
            "url": "https://www.youtube.com/channel/LH8D-9UHBa8I_L2pZhZfTN"
        })
        table.put_item(Item={
            "name": "test_channel_with_dupe_name",
            "url": "https://www.youtube.com/channel/SwW4CwHHWLQccd6Pu3nKha"
        })
        table.put_item(Item={
            "name": "test_channel_with_dupe_name",
            "url": "https://www.youtube.com/channel/MQKCcKfz5P4xhcpboXJK65"
        })
        table.put_item(Item={
            "name": "test_channel_host_blacklisted",
            "is_host_blacklisted": True,
            "url": "https://www.youtube.com/channel/GxFTPcP3jQvfmkDgkaeeeP"
        }),
        table.put_item(Item={
            "name": "test_channel_guest_blacklisted",
            "is_guest_blacklisted": True,
            "url": "https://www.youtube.com/channel/ZLe5IzkSGQaDtd6VqgDE3i"
        })
        table.put_item(Item={
            "created_at": "2018-10-21T10:52:42Z",
            "n_followers": 105,
            "n_followings": 175,
            "n_likes": 336,
            "n_tweets": 567,
            "name": "test_channel_with_rich_info",
            "twitter_url": "https://twitter.com/test_twitter_url",
            "url": "https://www.youtube.com/channel/UC-_HZgzcDWuPT39nQQyAJDa"
        })

        yield table


def test_found(table):
    event = read_json("tests/aws_event/dynamodb/Videos/with_mention.json")
    video, channel_names = main(event, table)

    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_title"
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


def test_rich_info(table):
    event = read_json("tests/aws_event/dynamodb/Videos/with_mention_rich_info.json")
    video, channel_names = main(event, table)

    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_title"
    assert channel_names == {"test_channel_0", "test_channel_with_rich_info"}


def test_duplicate_channel_names(table):
    event = read_json("tests/aws_event/dynamodb/Videos/dupe_channel_name.json")
    video, channel_names = main(event, table)

    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_title"
    assert channel_names == {"test_channel_with_dupe_name"}


def test_host_blacklisted(table):
    event = read_json("tests/aws_event/dynamodb/Videos/host_blacklisted.json")
    video, channel_names = main(event, table)

    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_title"
    assert channel_names == set()


def test_guest_blacklisted(table):
    event = read_json("tests/aws_event/dynamodb/Videos/guest_blacklisted.json")
    video, channel_names = main(event, table)

    assert video.url == "https://www.youtube.com/watch?v=test_video"
    assert video.title == "test_title"
    assert channel_names == {"test_channel_0"}
