import re
import sys
from typing import Optional
from urllib.parse import urlparse, parse_qs

sys.path.append("lib")

from lib.googleapiclient.discovery import build


class YoutubeVideo:
    def __init__(self, url: str, channel_id=None, title=None,
                 description=None, published_at=None, tags=None, thumbnails=None,
                 live_broadcast_content=None, n_watch=None, n_like=None,
                 category_id=None, default_language=None, localized=None):
        if is_valid_youtube_video_url(url):
            self.url = url
            self.id = parse_qs(urlparse(url).query)['v'][0]
            self.channel_id = channel_id
            self.title = title
            self.description = description
            self.published_at = published_at
            self.tags = tags
            self.thumbnails = thumbnails
            self.live_broadcast_content = live_broadcast_content
            self.n_watch = n_watch
            self.n_like = n_like
            self.category_id = category_id
            self.default_language = default_language
            self.localized = localized
        else:
            raise ValueError(f"{url} is not a valid YouTube video URL.")


class YouTube:
    def __init__(self, secret: str, version: str = "v3", http=None):
        self.youtube = build("youtube", version,
                             developerKey=secret, http=http)

    def _get_video_by_id(self, video_id: str) -> dict:
        req = self.youtube.videos().list(part="snippet", id=video_id)
        return req.execute()

    def get_video_by_id(self, video_id: str) -> Optional[dict]:
        res = self._get_video_by_id(video_id)
        items = res['items']

        if len(items) == 0:
            return None
        else:
            return items[0]

    def get_video_detail(self, video: YoutubeVideo) -> Optional[YoutubeVideo]:
        res = self.get_video_by_id(video.id)

        if res is None:
            return None
        else:
            s = res["snippet"]

            return YoutubeVideo(
                url=video.url,
                n_watch=video.n_watch,
                n_like=video.n_like,
                channel_id=s.get('channelId'),
                title=s.get('title'),
                description=s.get('description'),
                published_at=s.get('publishedAt'),
                tags=s.get('tags', []),
                thumbnails=s.get('thumbnails'),
                live_broadcast_content=s.get('liveBroadcastContent', 'none'),
                category_id=s.get('categoryId'),
                default_language=s.get('defaultLanguage'),
                localized=s.get('localized')
            )


def is_valid_youtube_video_url(url: str) -> bool:
    o = urlparse(url)
    qs = parse_qs(o.query)

    return o.scheme == 'https' \
        and o.netloc == 'www.youtube.com' \
        and o.path == '/watch' \
        and 'v' in qs \
        and re.fullmatch(r"[a-zA-Z0-9_\-]+", qs['v'][0]) is not None
