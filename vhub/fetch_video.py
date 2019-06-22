import gzip
import io
import json
import os
import re
import sys
import urllib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Tuple, Iterable, Union, List, Optional
from .youtube import YouTube, YoutubeVideo

sys.path.append("lib")

from lib import boto3
from lib.boto3_type_annotations import s3, dynamodb
from lib.toolz.dicttoolz import valmap, assoc


def dict_to_dynamo_item(obj: Union[dict, list, str, int]) -> dict:
    if isinstance(obj, dict):
        return valmap(dict_to_dynamo_item, obj)
    elif isinstance(obj, list):
        xs = list(map(dict_to_dynamo_item, obj))
        return {'L': xs}
    elif isinstance(obj, str):
        return {'S': obj}
    elif isinstance(obj, int):
        return {'I': obj}
    

def save_video(table: dynamodb.Table, video: YoutubeVideo):
    channels = mentioned_channel_urls(video)
    dic = assoc(vars(video), "mentioned_channels", channels)
    item = dict_to_dynamo_item(dic)
    
    table.put_item(Item=item)


def get_previous_object(obj: s3.Object) -> Optional[s3.Object]:
    client = boto3.client('s3')
    bucket = obj.bucket_name
    key = obj.key
    response = client.list_objects_v2(
        Bucket=bucket,
        StartAfter=key,
        MaxKeys=1
    )
    contents = response['Contents']

    if len(contents) == 0:
        return None
    else:
        key_prev = contents[0]['Key']
        return boto3.resource('s3').Object(bucket, key_prev)


def extract_html(obj: s3.Object) -> str:
    response = obj.get()
    body = response['Body'].read()
    with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as fh:
        dic = json.load(fh)
        return dic['body']


def parse_videos_list(html: str) -> Iterable[YoutubeVideo]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except:
        soup = BeautifulSoup(html, "html5lib")

    for table in soup.select("table"):
        for video in table.select("tbody > tr"):
            def f(selector: str) -> int:
                elem = video.select_one(selector).next_sibling
                return int(elem.string.strip().replace(',', ''))
            
            yield YoutubeVideo(
                url = video['data-video-url'],
                n_watch = f('i.fa-eye'),
                n_like = f('i.fa-thumbs-up')
            )


def get_new_videos(new: s3.Object, prev: Optional[s3.Object]) -> Iterable[YoutubeVideo]:
    new_videos = parse_videos_list(extract_html(new))

    if prev is None:
        return set(new_videos)
    else:
        prev_videos = parse_videos_list(extract_html(new))
        return set(new_videos) - set(prev_videos)


def mentioned_channel_urls(video: YoutubeVideo) -> List[str]:
    if video.description is None:
        return []
    else:
        channel_url_regex = r"https:\/\/www\.youtube\.com\/channel\/[a-zA-Z0-9]+"
        return re.findall(channel_url_regex, video.description)


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    new_obj = boto3.resource('s3').Object(bucket, key)
    prev_obj = get_previous_object(new_obj)
    new_videos = get_new_videos(new_obj, prev_obj)
    
    youtube_api_key = os.environ['GOOGLE_CLOUD_API_KEY']
    youtube = YouTube(youtube_api_key)

    video_details = map(youtube.get_video_detail, new_videos)

    table = boto3.resource('dynamodb').Table('Videos')

    for video in video_details:
        save_video(table, video)