import boto3
import gzip
import io
import json
import logging
import os
import sys
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Tuple, Iterable, Union, List, Optional
from .youtube import YouTube, YoutubeVideo

sys.path.append("lib")
sys.path.append("lib.bs4")

from bs4 import BeautifulSoup
from lib.boto3_type_annotations import s3, dynamodb
from lib.toolz.dicttoolz import valmap, assoc


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def emptystr_to_none(item):
    if isinstance(item, list):
        return list(map(emptystr_to_none, item))
    if isinstance(item, dict):
        return valmap(emptystr_to_none, item)
    else:
        return None if item == "" else item


def save_video(table: dynamodb.Table, video: YoutubeVideo):
    item = emptystr_to_none(vars(video))

    try:
        table.put_item(Item=item)
        logger.info('Successfully saved a YouTube video: %s', video)
    except ClientError as e:
        logger.error('Failed to save a YouTube video: %s', video)
        logger.exception('The reason being: %s', e)


def get_previous_object(obj: s3.Object) -> Optional[s3.Object]:
    client = boto3.client('s3')
    bucket = obj.bucket_name
    key = obj.key
    response = client.list_objects_v2(
        Bucket=bucket,
        StartAfter=key,
        MaxKeys=1
    )

    if response['KeyCount'] == 0:
        return None
    else:
        key_prev = response['Contents'][0]['Key']
        return boto3.resource('s3').Object(bucket, key_prev)


def extract_html(obj: s3.Object) -> str:
    response = obj.get()
    body = response['Body'].read()
    with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as fh:
        dic = json.load(fh)
        return dic['body']


def parse_videos_list(html: str) -> Iterable[YoutubeVideo]:
    """
    Parse the web page: https://vtuber-antenna.net/new/.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except:
        soup = BeautifulSoup(html, "html5lib")

    videos = soup.select("div#main-area div.movie ul.movieList.new li:not(.empty)")

    for video in videos:
        a = video.select_one("p.movieTitle a")
        url = a["href"]

        yield YoutubeVideo(url)


def get_new_videos(new: s3.Object, prev: Optional[s3.Object]) -> Iterable[YoutubeVideo]:
    new_videos = parse_videos_list(extract_html(new))

    if prev is None:
        return set(new_videos)
    else:
        prev_videos = parse_videos_list(extract_html(prev))
        return set(new_videos) - set(prev_videos)


def get_video_details(videos: Iterable[YoutubeVideo], youtube: YouTube):
    for video in videos:
        try:
            detail = youtube.get_video_detail(video)
            if detail is not None:
                yield detail
        except Exception as e:
            logger.error('YouTube API gave an error while getting details of the video: %s', video.url)
            logger.exception('The reason being: %s', e)


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    new_obj = boto3.resource('s3').Object(bucket, key)
    prev_obj = get_previous_object(new_obj)
    new_videos = get_new_videos(new_obj, prev_obj)

    logger.info("New version of the crawled webpage: %s", new_obj.key)
    if prev_obj is not None:
        logger.info("Previous version of the crawled webpage: %s", prev_obj.key)
    logger.info('New videos: %s', [video.url for video in new_videos])
    
    youtube_api_key = os.environ['GOOGLE_CLOUD_API_KEY']
    youtube = YouTube(youtube_api_key)

    video_details = get_video_details(new_videos, youtube)

    table = boto3.resource('dynamodb').Table('Videos')

    for video in video_details:
        save_video(table, video)
