import json
import sys
import unittest
from fetch_video import parse_videos_list
from youtube import is_valid_youtube_video_url, YouTube

sys.path.append('lib')

from lib.googleapiclient.http import HttpMockSequence


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


api_discovery = read_file("tests/api_responses/youtube/discovery.json")
PLACE_HOLDER = ""


class TestIsValidYoutubeVideoUrl(unittest.TestCase):
    def test_alphanumeric_only_id(self):
        url = "https://www.youtube.com/watch?v=uaQS2ZnrFQg"
        self.assertTrue(is_valid_youtube_video_url(url))

    def test_underscore_containing_id(self):
        url = "https://www.youtube.com/watch?v=RnDf_nvcx3A"
        self.assertTrue(is_valid_youtube_video_url(url))

    def test_hyphen_containing_id(self):
        url = "https://www.youtube.com/watch?v=-_xY7wNvw9k"
        self.assertTrue(is_valid_youtube_video_url(url))

    def test_invalid_url(self):
        url = "https://www.example.com/"
        self.assertFalse(is_valid_youtube_video_url(url))


class TestGetVideoById(unittest.TestCase):
    def test_found(self):
        id = "03H1qSot9_s"
        response = read_file("tests/api_responses/youtube/videos/list/no_mention.json")
        http = HttpMockSequence([
            ({"status": 200}, api_discovery),
            ({"status": 200}, response)
        ])
        youtube = YouTube(secret=PLACE_HOLDER, http=http)
        
        out = youtube.get_video_by_id(id)
        ground_truth = json.loads(response)['items'][0]

        self.assertEqual(out['id'], id)
        self.assertDictEqual(out, ground_truth)
    
    def test_not_found(self):
        id = PLACE_HOLDER
        response = read_file("tests/api_responses/youtube/videos/list/not_found.json")
        http = HttpMockSequence([
            ({"status": 200}, api_discovery),
            ({"status": 200}, response)
        ])
        youtube = YouTube(secret=PLACE_HOLDER, http=http)

        with self.assertRaises(ValueError):
            youtube.get_video_by_id(id)
