import boto3
import requests
import requests_mock
import unittest
from moto import mock_s3
from vhub.fetch_vtuber_antenna import save_zipped_response


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


class TestSaveZippedResponse(unittest.TestCase):
    @mock_s3
    def test(self):
        bucket_name = "crawled-webpage"
        bucket = boto3.resource("s3").Bucket(bucket_name)

        with requests_mock.Mocker() as m:
            m.get('http://example.com', text='test')
            response = requests.get('http://example.com')

        bucket.create()
        save_zipped_response(response, bucket)
