import gzip
import io
import json
import os
import re
import sys
import urllib
from datetime import datetime, timedelta
from typing import Tuple, Iterable, Union, List
from youtube import YouTube, YoutubeVideo

sys.path.append("lib")

from lib import boto3
from lib.boto3_type_annotations import s3, dynamodb
from lib.bs4 import BeautifulSoup
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


def get_latest_two_files(client: s3.Client, bucket: str, prefix: str) -> Tuple[s3.Object, s3.Object]:
    an_hour_before = datetime.utcnow() - timedelta(hours=1)
    timestamp = an_hour_before.replace(microsecond=0).isoformat().replace(':', '-')
    
    response = client.list_objects_v2(StartAfter=f"{prefix}/{timestamp}", MaxKeys=2)
    keys = (content['Key'] for content in response['Contents'])

    buck = client.Bucket(bucket)
    prev, new = [buck.Object(key) for key in keys]

    return (prev, new)


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
            yield YoutubeVideo(
                url = video['data-video-url'],
                n_watch = int(video.select("i.fa-eye").text),
                n_like = int(video.select("i.fa-thumbs-up"))
            )


def get_new_videos(prev_html: str, new_html: str) -> Iterable[YoutubeVideo]:
    prev_videos = parse_videos_list(prev_html)
    new_videos = parse_videos_list(new_html)
    return set(new_videos) - set(prev_videos)


def mentioned_channel_urls(video: YoutubeVideo) -> List[str]:
    if video.description is None:
        return []
    else:
        channel_url_regex = r"https:\/\/www\.youtube\.com\/channel\/[a-zA-Z0-9]+"
        return re.findall(channel_url_regex, video.description)


def lambda_handler(event, context):
    client = boto3.client('s3')
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    bucket = client.Bucket(bucket_name)

    prefix = 'vtuber-ranking'
    objs = get_latest_two_files(client, bucket, prefix)
    htmls = [extract_html(obj) for obj in objs]
    new_videos = get_new_videos(*htmls)
    
    youtube_api_key = os.environ['GOOGLE_CLOUD_API_KEY']
    youtube = YouTube(youtube_api_key)

    video_details = map(youtube.get_video_detail, new_videos)

    table = boto3.resource('dynamodb').Table('Videos')

    for video in video_details:
        save_video(table, video)