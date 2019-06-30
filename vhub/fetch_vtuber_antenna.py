import boto3
import logging
import json
import sys
from gzip import GzipFile
from io import BytesIO
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

sys.path.append("lib")

from lib import requests
from lib.boto3_type_annotations import s3


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def make_obj(response: requests.Response) -> dict:
    try:
        date = parsedate_to_datetime(response.headers["Date"])
    except:
        date = datetime.now(timezone.utc)

    return {
        "url": response.url,
        "body": response.text,
        "crawled_at": date
    }


def reverse_timestamp(date: datetime):
    date_max = datetime.max.replace(tzinfo=timezone.utc)
    return str(int((date_max - date).total_seconds()))


def gzip_str(string: str) -> bytes:
    out = BytesIO()

    with GzipFile(fileobj=out, mode='w') as f:
        f.write(string.encode())

    return out.getvalue()


def upload_zip(obj: s3.Object, body: str):
    obj.put(Body=gzip_str(body), ContentEncoding="gzip")


def save_zipped_response(response: requests.Response, bucket: s3.Bucket):
    dic = make_obj(response)
    body = json.dumps(dic, default=str)
    timestamp = reverse_timestamp(dic["crawled_at"])
    key = f"{timestamp}.json.gz"
    obj = bucket.Object(key)

    upload_zip(obj, body)


def lambda_handler(event, context):
    bucket_name = "crawled-webpages-vtuber-antenna"
    url = "https://vtuber-antenna.net/new/"

    bucket = boto3.resource("s3").Bucket(bucket_name)
    response = requests.get(url)

    if response.ok:
        save_zipped_response(response, bucket)
    else:
        logger.warn("The request to '%s' failed with the status code `%s`.",
                    response.url, response.status_code)
        logger.warn(response.text)
