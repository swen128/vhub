import boto3
import json
import unittest
from moto import mock_dynamodb2, mock_s3
from textwrap import dedent
from vhub.notifier import mentioned_channel_urls, video_from_event, message
from vhub.youtube import YoutubeVideo


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
