import gzip
import io
import json
import os
import sys
from bs4 import BeautifulSoup
from typing import Tuple, Iterable, Union, List, Optional
from .youtube import YoutubeChannel

sys.path.append("lib")

from lib import boto3
from lib.boto3_type_annotations import s3, dynamodb


def save_channel(table: dynamodb.Table, channel: YoutubeChannel):
    table.put_item(Item=vars(channel))


def extract_html(obj: s3.Object) -> str:
    response = obj.get()
    body = response['Body'].read()
    with gzip.GzipFile(fileobj=io.BytesIO(body), mode='rb') as fh:
        dic = json.load(fh)
        return dic['body']


def parse_channel_info(html: str) -> YoutubeChannel:
    try:
        soup = BeautifulSoup(html, "lxml")
    except:
        soup = BeautifulSoup(html, "html5lib")

    raise NotImplementedError()


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    obj = boto3.resource('s3').Object(bucket, key)
    html = extract_html(obj)
    channel = parse_channel_info(html)

    table = boto3.resource('dynamodb').Table('Channels')

    save_channel(table, channel)