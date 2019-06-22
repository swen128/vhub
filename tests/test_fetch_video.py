import sys
import unittest
from moto import mock_dynamodb2
from vhub.fetch_video import parse_videos_list, save_video, dict_to_dynamo_item
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


class TestDictToDynamoItem(unittest.TestCase):
    def test_small_dict(self):
        dic = {"a": 1, "b": ["2", "3"]}
        out = dict_to_dynamo_item(dic)
        ground_truth = {"a": {"I": 1}, "b": {"L": [{"S": "2"}, {"S": "3"}]}}

        self.assertDictEqual(out, ground_truth)

    def test_invalid_dict(self):
        dic = {"a": None}
        with self.assertRaises(ValueError):
            dict_to_dynamo_item(dic)


class TestSaveVideo(unittest.TestCase):
    @mock_dynamodb2
    def test_video(self):
        video = YoutubeVideo("https://www.youtube.com/watch?v=-_xY7wNvw9k")

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
