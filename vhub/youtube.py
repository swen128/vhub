import re
from googleapiclient.discovery import build
from typing import Optional, List
from urllib.parse import urlparse, parse_qs


class YoutubeVideo:
    def __init__(self, url: str, channel_url=None, title=None,
                 description=None, published_at=None, tags=None, thumbnails=None,
                 channel_title=None, live_broadcast_content=None, n_watch=None, n_like=None,
                 category_id=None, default_language=None, localized=None):
        if is_valid_youtube_video_url(url):
            self.url = url
            self.channel_url = channel_url
            self.channel_title = channel_title
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

    def __str__(self):
        return str(vars(self))

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, YoutubeVideo) and self.url == other.url


class YouTube:
    def __init__(self, secret: str, version: str = "v3", http=None):
        self.youtube = build("youtube", version,
                             developerKey=secret, http=http, cache_discovery=False)

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
        video_id = parse_qs(urlparse(video.url).query)['v'][0]
        res = self.get_video_by_id(video_id)

        if res is None:
            return None
        else:
            s = res["snippet"]
            base_url = "https://www.youtube.com/channel"
            channel_id = s.get('channelId')
            channel_url = f"{base_url}/{channel_id}" if 'channelId' in s else None

            return YoutubeVideo(
                url=video.url,
                n_watch=video.n_watch,
                n_like=video.n_like,
                channel_url=channel_url,
                channel_title=s.get('channelTitle'),
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


class YoutubeChannel:
    def __init__(self, url, name=None, n_subscriber=None):
        if is_valid_youtube_channel_url(url):
            self.url = url
            self.name = name
            self.n_subscriber = n_subscriber
        else:
            raise ValueError(f"{url} is not a valid YouTube channel URL.")


def is_valid_youtube_channel_url(url: str) -> bool:
    channel_url_regex = r"https:\/\/www\.youtube\.com\/(?:channel|c|user)\/[a-zA-Z0-9_\-]+"
    match = re.fullmatch(channel_url_regex, url)
    return match is not None


def mentioned_channel_urls(video: YoutubeVideo) -> List[str]:
    if video.description is None:
        return []
    else:
        channel_url_regex = r"https:\/\/www\.youtube\.com\/(?:channel|c|user)\/[a-zA-Z0-9_\-]+"
        urls = re.findall(channel_url_regex, video.description)
        return list(set(urls) - {video.channel_url})


def is_valid_youtube_video_url(url: str) -> bool:
    o = urlparse(url)
    qs = parse_qs(o.query)

    return o.scheme == 'https' \
        and o.netloc == 'www.youtube.com' \
        and o.path == '/watch' \
        and 'v' in qs \
        and re.fullmatch(r"[a-zA-Z0-9_\-]+", qs['v'][0]) is not None


def short_youtube_video_url(url: str) -> str:
    if is_valid_youtube_video_url(url):
        o = urlparse(url)
        video_id = parse_qs(o.query)['v'][0]
        return f"https://youtu.be/{video_id}"