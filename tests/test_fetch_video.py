import boto3
import pytest
from moto import mock_dynamodb2, mock_s3

from vhub.fetch_video import parse_videos_list, main, save_video
from vhub.utils import read_file, read_json
from vhub.youtube import YoutubeVideo


class MockYouTube:
    def get_video_detail(self, video: YoutubeVideo) -> YoutubeVideo:
        return YoutubeVideo("https://www.youtube.com/watch?v=test_video")


@pytest.fixture
def table():
    with mock_dynamodb2():
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
        yield db.Table('Videos')


@pytest.fixture
def setup_s3():
    with mock_s3():
        s3_client = boto3.resource('s3')
        bucket = s3_client.Bucket('crawled-webpages')
        event = read_json('tests/aws_event/s3/crawled-webpages/put.json')

        bucket.create()

        def put_gzip(key):
            path = f'tests/s3_object/{key}'
            with open(path, mode='rb') as f:
                bucket.put_object(Key=key, Body=f, ContentEncoding='gzip')

        put_gzip('251839840704.json.gz')
        put_gzip('251839841004.json.gz')

        yield event, s3_client


def test_main(setup_s3):
    event, s3_client = setup_s3
    youtube = MockYouTube()

    videos = list(main(event, s3_client, youtube))

    assert len(videos) == 2

    for video in videos:
        assert isinstance(video, YoutubeVideo)


def test_parse_minimal_html():
    html = read_file('tests/html/vtuber_antenna/minimal.html')
    videos = parse_videos_list(html)

    for video in videos:
        assert isinstance(video, YoutubeVideo)


def test_parse_real_html():
    html = read_file('tests/html/vtuber_antenna/real.html')
    videos = parse_videos_list(html)

    for video in videos:
        assert isinstance(video, YoutubeVideo)


def test_save_video(table):
    url = "https://www.youtube.com/watch?v=test_video"
    video = YoutubeVideo(url=url, title="")

    save_video(table, video)

    response = table.get_item(Key={"url": url})
    out = response['Item']

    assert out['url'] == url
    assert out['title'] is None


def test_save_video_with_empty_string(table):
    """
    DynamoDB does not accept objects with an empty string in its attribute.
    See, e.g., https://github.com/aws/aws-sdk-java/issues/1189

    The function `save_video` thus should replace empty strings with `None` before saving.
    """
    url = "https://www.youtube.com/watch?v=test_video"
    video = YoutubeVideo(url=url, title="title", description="description")

    save_video(table, video)

    response = table.get_item(Key={"url": url})
    out = response['Item']

    assert out == vars(video)
