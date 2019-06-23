import json
import sys
import unittest
from moto import mock_dynamodb2, mock_s3
from textwrap import dedent
from vhub.notifier import dict_from_dynamo_item, mentioned_channel_urls, video_from_event, message
from vhub.youtube import YoutubeVideo

sys.path.append("lib")

from lib import boto3


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


class TestMentionedChannelUrls(unittest.TestCase):
    def test_self_mention(self):
        url = "https://www.youtube.com/channel/UCD-miitqNY3nyukJ4Fnf4_A"
        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=03H1qSot9_s",
            channel_url=url,
            description=f"My channel: {url}"
        )

        out = mentioned_channel_urls(video)
        
        self.assertEqual(out, [url])

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
        
        self.assertSetEqual(set(out), {url_1, url_2, url_3})


class TestDictFromDynamoItem(unittest.TestCase):
    def test_simple(self):
        dic = {"a": {"I": 1}, "b": {"L": [{"S": "2"}, {"S": "3"}]}}
        out = dict_from_dynamo_item(dic)
        ground_truth = {"a": 1, "b": ["2", "3"]}

        self.assertEqual(out, ground_truth)


class TestVideoFromEvent(unittest.TestCase):
    def test_simple(self):
        event_raw = read_file('tests/aws_event/dynamodb/new_video.json')
        event = json.loads(event_raw)
        out = video_from_event(event)
        ground_truth = YoutubeVideo(
            url="https://www.youtube.com/watch?v=KNi82VggtBo",
            title="title",
            description="description"
        )

        self.assertDictEqual(vars(out), vars(ground_truth))


class TestMessage(unittest.TestCase):
    def test_simple(self):
        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=KNi82VggtBo",
            title="title"
        )
        channels = [
            {'name': 'channel_1'},
            {'name': 'channel_2'}
        ]
        out = message(video, channels)
        ground_truth = dedent(
            """\
            #新着VTuberコラボ動画
            title
            https://www.youtube.com/watch?v=KNi82VggtBo
            
            【参加者】
            channel_1
            channel_2"""
        )

        self.assertMultiLineEqual(out, ground_truth)