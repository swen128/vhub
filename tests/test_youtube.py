import json
import unittest

from googleapiclient.http import HttpMockSequence

from vhub.utils import read_file
from vhub.youtube import is_valid_youtube_video_url, YouTube, YoutubeVideo

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

        out = youtube.get_video_by_id(id)
        self.assertIsNone(out)


class TestGetVideoDetail(unittest.TestCase):
    def test_found(self):
        video = YoutubeVideo(
            url="https://www.youtube.com/watch?v=03H1qSot9_s",
            n_watch=128,
            n_like=64
        )
        response = read_file("tests/api_responses/youtube/videos/list/no_mention.json")
        http = HttpMockSequence([
            ({"status": 200}, api_discovery),
            ({"status": 200}, response)
        ])
        youtube = YouTube(secret=PLACE_HOLDER, http=http)

        out = youtube.get_video_detail(video)

        self.assertIsInstance(out, YoutubeVideo)
        self.assertEqual(out.url, video.url)
        self.assertEqual(out.n_watch, video.n_watch)
        self.assertEqual(out.n_like, video.n_like)
        self.assertEqual(out.published_at, "2018-02-16T04:40:17.000Z")

    def test_not_found(self):
        video = YoutubeVideo("https://www.youtube.com/watch?v=invalid_id")
        response = read_file("tests/api_responses/youtube/videos/list/not_found.json")
        http = HttpMockSequence([
            ({"status": 200}, api_discovery),
            ({"status": 200}, response)
        ])
        youtube = YouTube(secret=PLACE_HOLDER, http=http)

        out = youtube.get_video_detail(video)

        self.assertIsNone(out)


class TestYouTubeVideoEq(unittest.TestCase):
    def test_equal(self):
        url = "https://www.youtube.com/watch?v=03H1qSot9_s"
        video_1 = YoutubeVideo(url)
        video_2 = YoutubeVideo(url)

        self.assertEqual(video_1, video_2)

    def test_not_equal(self):
        video_1 = YoutubeVideo("https://www.youtube.com/watch?v=03H1qSot9_s")
        video_2 = YoutubeVideo("https://www.youtube.com/watch?v=uaQS2ZnrFQg")

        self.assertNotEqual(video_1, video_2)
