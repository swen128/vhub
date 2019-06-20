import gzip
import io
import json
import sys
import urllib
from typing import Tuple, Iterator
from youtube import YouTube, YoutubeVideo

sys.path.append("lib")

from lib import boto3
from lib.boto3_type_annotations import s3, dynamodb


def save_video(table: dynamodb.Table, video: YoutubeVideo):
    raise NotImplementedError()


def get_latest_two_files(bucket: s3.Bucket, directory) -> Tuple[s3.Object, s3.Object]:
    raise NotImplementedError()


def extract_html(obj: s3.Object) -> str:
    response = obj.get()
    body = response['Body'].read()
    with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as fh:
        dic = json.load(fh)
        return dic['body']


def get_new_videos(prev_html: str, new_html: str) -> Iterator[YoutubeVideo]:
    raise NotImplementedError()


def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    bucket = boto3.client('s3').Bucket(bucket_name)

    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    directory = raise NotImplementedError()

    objs = get_latest_two_files(bucket, directory)
    htmls = [extract_html(obj) for obj in objs]
    new_videos = get_new_videos(*htmls)
    
    youtube_api_key = raise NotImplementedError()
    youtube = YouTube(youtube_api_key)

    video_details = map(youtube.get_video_detail, new_videos)

    table = boto3.resource('dynamodb').Table('Videos')

    for video in video_details:
        save(table, video)