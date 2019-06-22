import unittest
from fetch_video import parse_videos_list
from youtube import is_valid_youtube_video_url


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
