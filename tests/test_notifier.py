import boto3
import json
import unittest
from moto import mock_dynamodb2
from textwrap import dedent
from vhub.notifier import vtuber_channel_detail, mentioned_channel_urls, video_from_event, message
from vhub.utils import read_file
from vhub.youtube import YoutubeVideo


class TestVtuberChannelDetail(unittest.TestCase):
    @mock_dynamodb2
    def test_not_found(self):
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
        url = "https://www.youtube.com/channel/test"
        out = vtuber_channel_detail(url, table)

        self.assertIsNone(out)

    @mock_dynamodb2
    def test_found(self):
        url = "https://www.youtube.com/channel/test"
        item = {'url': url, 'name': 'name'}
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
        table.put_item(Item=item)
        
        out = vtuber_channel_detail(url, table)

        self.assertDictEqual(out, item)


class TestMentionedChannelUrls(unittest.TestCase):
    def test_self_mention(self):
        url = "https://www.youtube.com/channel/UCD-miitqNY3nyukJ4Fnf4_A"
        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=03H1qSot9_s",
            channel_url=url,
            description=f"My channel: {url}"
        )

        out = mentioned_channel_urls(video)
        
        self.assertEqual(out, [])

    def test_mentions(self):
        url_1 = "https://www.youtube.com/channel/UC6oDys1BGgBsIC3WhG1BovQ"
        url_2 = "https://www.youtube.com/channel/UCsg-YqdqQ-KFF0LNk23BY4A"
        url_3 = "https://www.youtube.com/channel/UCD-miitqNY3nyukJ4Fnf4_A"

        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=vHl9Tx-HJHw",
            channel_url=url_3,
            description=f"{url_1} {url_2} {url_3}"
        )

        out = mentioned_channel_urls(video)
        
        self.assertSetEqual(set(out), {url_1, url_2})


class TestVideoFromEvent(unittest.TestCase):
    def test_simple(self):
        event_raw = read_file('tests/aws_event/dynamodb/new_video.json')
        event = json.loads(event_raw)
        out = video_from_event(event)
        ground_truth = YoutubeVideo(
            url="https://www.youtube.com/watch?v=KNi82VggtBo",
            title="title",
            description="description",
            tags=["VTuber", "vtuber"],
            default_language=None
        )

        self.assertDictEqual(vars(out), vars(ground_truth))


class TestMessage(unittest.TestCase):
    def test_simple(self):
        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=KNi82VggtBo",
            title="title"
        )
        channels = [
            {'name': 'host_channel'},
            {'name': 'channel_1'},
            {'name': 'channel_2'}
        ]
        out = message(video, channels)
        
        mes_short = dedent(
            """\
            #VTuberコラボ通知
            https://youtu.be/KNi82VggtBo"""
        )
        mes_mid = dedent(
            """\
            #VTuberコラボ通知
            title
            https://youtu.be/KNi82VggtBo"""
        )
        mes_long = dedent(
            """\
            #VTuberコラボ通知
            https://youtu.be/KNi82VggtBo
            
            【参加者】
            host_channel
            channel_1
            channel_2"""
        )
        mes_max = dedent(
            """\
            #VTuberコラボ通知
            title
            https://youtu.be/KNi82VggtBo
            
            【参加者】
            host_channel
            channel_1
            channel_2"""
        )
        ground_truth = [mes_max, mes_long, mes_mid, mes_short]

        self.assertListEqual(out, ground_truth)


