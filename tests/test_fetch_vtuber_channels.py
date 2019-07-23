import boto3
import pytest
import requests
import requests_mock
from moto import mock_dynamodb2

from vhub.fetch_vtuber_channels import parse_vtubers_list, main, save_channel
from vhub.utils import read_file
from vhub.youtube import YoutubeChannel


def mock_request(url: str, text: str, headers: dict = {}, method: str = 'GET') -> requests.Response:
    with requests_mock.Mocker() as m:
        m.register_uri(method, url, text=text, headers=headers)
        return requests.get(url)


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
        yield db.Table('Channels')


def test_main(table):
    url = 'https://vtuber-antenna.net/list/'
    body = read_file('tests/html/vtuber_antenna/list/minimal.html')
    response = mock_request(url, body)

    main(response, table)

    channel_url = 'https://www.youtube.com/channel/UCp6993wxpyDPHUpavwDFqgg'
    db_response = table.get_item(Key={'url': channel_url})
    out = db_response['Item']

    assert out['url'] == channel_url
    assert out['name'] == 'SoraCh. ときのそらチャンネル'
    assert out['thumbnail'] == \
        'https://yt3.ggpht.com/a/AGF-l79dHleIBmBtLP2TfcmFpIJjmH7fa8tfG1qTKg=s240-mo-c-c0xffffffff-rj-k-no'
    assert set(out['affiliations']) == {'カバー', 'ホロライブ'}


def test_parse_minimal_html():
    html = read_file('tests/html/vtuber_antenna/list/minimal.html')
    channels = list(parse_vtubers_list(html))

    assert len(channels) == 1

    for channel in channels:
        assert isinstance(channel, YoutubeChannel)


def test_parse_real_html():
    html = read_file('tests/html/vtuber_antenna/list/real.html')
    channels = list(parse_vtubers_list(html))

    assert len(channels) == 1142

    for channel in channels:
        assert isinstance(channel, YoutubeChannel)


def test_save_channel(table):
    url = "https://www.youtube.com/channel/UC4LhEy6ZGQ2XtvFd5jmiNG"
    channel = YoutubeChannel(url=url, name="test_channel")

    save_channel(table, channel)

    response = table.get_item(Key={"url": url})
    out = response['Item']

    assert out['url'] == url
    assert out['name'] == "test_channel"
