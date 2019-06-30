import boto3
import sys
import unittest
from moto import mock_dynamodb2, mock_s3
from vhub.fetch_video import parse_videos_list, save_video, get_previous_object
from vhub.utils import read_file
from vhub.youtube import YoutubeVideo


class TestParseVideosList(unittest.TestCase):
    def test_minimal_html(self):
        html = read_file('tests/html/vtuber_antenna/minimal.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)

    def test_real_html(self):
        html = read_file('tests/html/vtuber_antenna/real.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)


class TestSaveVideo(unittest.TestCase):
    @mock_dynamodb2
    def test_empty_string(self):
        """
        DynamoDB does not accept objects with an empty string in its attribute.
        See, e.g., https://github.com/aws/aws-sdk-java/issues/1189

        The function `save_video` thus should replace empty strings with `None` before saving.
        """
        url = "https://www.youtube.com/watch?v=03H1qSot9_s"
        video = YoutubeVideo(url=url, title="")
        
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
        self.assertEqual(out['title'], None)

    @mock_dynamodb2
    def test_video(self):
        url = "https://www.youtube.com/watch?v=03H1qSot9_s"
        video = YoutubeVideo(
            url=url,
            n_watch=1,
            n_like=1,
            channel_url="https://www.youtube.com/channel/UCD-miitqNY3nyukJ4Fnf4_A",
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
        ground_truth = vars(video)

        self.assertDictEqual(out, ground_truth)


class TestGetPreviousObject(unittest.TestCase):
    @mock_s3
    def test_empty_bucket(self):
        s3 = boto3.resource('s3', region_name='us-east-2')
        s3.create_bucket(Bucket='crawled-webpages')
        
        obj = s3.Object('crawled-webpages', 'key')

        out = get_previous_object(obj)

        self.assertEqual(out, None)

    @mock_s3
    def test_found(self):
        s3 = boto3.resource('s3', region_name='us-east-2')
        bucket = s3.Bucket('crawled-webpages')
        obj_1 = bucket.Object('1')
        obj_2 = bucket.Object('2')

        bucket.create()
        obj_1.put()
        obj_2.put()

        out = get_previous_object(obj_1)

        self.assertEqual(out.key, obj_2.key)
