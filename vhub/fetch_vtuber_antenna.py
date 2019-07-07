import boto3
import logging
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Tuple
from .utils import utc_now, reverse_timestamp, gzip_str

sys.path.append("lib")

from lib import requests
from lib.boto3_type_annotations import s3


logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class PageItem:
    url: str
    body: str
    crawled_at: datetime


def page_item_from_response(response: requests.Response) -> PageItem:
    try:
        date = parsedate_to_datetime(response.headers["Date"])
    except:
        date = utc_now()

    return PageItem(
        url=response.url,
        body=response.text,
        crawled_at=date
    )


def save_zipped(obj: s3.Object, body: str):
    obj.put(Body=gzip_str(body), ContentEncoding="gzip")


def save_page(obj: s3.Object, page: PageItem):
    body = json.dumps(asdict(page), default=str)
    save_zipped(obj, body)


def main(response: requests.Response, bucket: s3.Bucket) -> Tuple[s3.Object, PageItem]:
    page = page_item_from_response(response)
    timestamp = reverse_timestamp(page.crawled_at)
    key = f"{timestamp}.json.gz"
    obj = bucket.Object(key)

    return (obj, page)


def lambda_handler(event, context):
    bucket_name = "crawled-webpages-vtuber-antenna"
    url = "https://vtuber-antenna.net/new/"
    response = requests.get(url)

    if response.ok:
        bucket = boto3.resource("s3").Bucket(bucket_name)
        obj, page = main(response, bucket)
        save_page(obj, page)
    else:
        logger.warn("The request to '%s' failed with the status code `%s`.",
                    response.url, response.status_code)
        logger.warn(response.text)
