import sys
import unittest
from moto import mock_dynamodb2
from vhub.fetch_video import parse_videos_list, save_video
from vhub.youtube import YoutubeVideo

sys.path.append("lib")

from lib import boto3


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


class TestParseVideosList(unittest.TestCase):
    def test_minimal_html(self):
        html = read_file('tests/html/vtuber_ranking/minimal.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)

    def test_real_html(self):
        html = read_file('tests/html/vtuber_ranking/real.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)


class TestSaveVideo(unittest.TestCase):
    @mock_dynamodb2
    def test_video(self):
        url = "https://www.youtube.com/watch?v=03H1qSot9_s"
        video = YoutubeVideo(
            url=url,
            n_watch=1,
            n_like=1,
            channel_id="UCD-miitqNY3nyukJ4Fnf4_A",
            title="title",
            description="description",
            published_at="2018-02-16T04:40:17.000Z",
            tags=["UCD-miitqNY3nyukJ4Fnf4_A", "tag"],
            thumbnails={
                "default": {
                    "url": "https://i.ytimg.com/vi/03H1qSot9_s/default.jpg",
                    "width": 120,
                    "height": 90
                },
                "medium": {
                    "url": "https://i.ytimg.com/vi/03H1qSot9_s/mqdefault.jpg",
                    "width": 320,
                    "height": 180
                },
                "high": {
                    "url": "https://i.ytimg.com/vi/03H1qSot9_s/hqdefault.jpg",
                    "width": 480,
                    "height": 360
                }
            },
            live_broadcast_content="none",
            category_id="20",
            default_language="en",
            localized={
                "title": "title",
                "description": "description"
            }
        )

        db = boto3.resource('dynamodb', region_name='us-east-2')
        db.create_table(
        TableName='Videos',
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
        table = db.Table('Videos')

        save_video(table, video)
        
        response = table.get_item(Key={"url": url})
        out = response['Item']

        self.assertEqual(out['url'], url)
        self.assertEqual(out['title'], "title")
