import boto3
import pytest
import requests
import requests_mock
from moto import mock_s3

from vhub.fetch_vtuber_antenna import main


def mock_request(url: str, text: str, headers: dict = {}, method: str = 'GET') -> requests.Response:
    with requests_mock.Mocker() as m:
        m.register_uri(method, url, text=text, headers=headers)
        return requests.get(url)


@pytest.fixture
def bucket():
    with mock_s3():
        bucket_name = "crawled-webpage"
        bucket = boto3.resource("s3").Bucket(bucket_name)
        bucket.create()
        yield bucket


def test_page_item_represents_the_response_page(bucket):
    url = 'http://example.com/'
    body = 'test_body'
    response = mock_request(url, body)

    obj, page = main(response, bucket)

    assert obj.bucket_name == bucket.name
    assert page.url == url
    assert page.body == body


def test_newer_object_has_smaller_key(bucket):
    url = 'http://example.com/'
    body = 'test_body'

    response_prev = mock_request(
        url, body, headers={"Date": "Wed, 21 Oct 2015 07:28:00 GMT"})
    response_next = mock_request(
        url, body, headers={"Date": "Wed, 21 Oct 2015 07:30:00 GMT"})

    obj_prev, _ = main(response_prev, bucket)
    obj_next, _ = main(response_next, bucket)

    assert obj_prev.key > obj_next.key
