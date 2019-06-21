import unittest
from fetch_video import parse_videos_list
from youtube import YoutubeVideo


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


class TestParseVideosList(unittest.TestCase):
    def test_minimal_html(self):
        html = read_file('tests/html/vtuber_ranking/minimal.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)

    def test_real_html(self):
        html = read_file('tests/html/vtuber_ranking/real.html')
        videos = parse_videos_list(html)

        for video in videos:
            self.assertIsInstance(video, YoutubeVideo)