import json
import yaml
from datetime import datetime, timezone
from gzip import GzipFile
from io import BytesIO

from toolz.dicttoolz import valmap


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


def read_json(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def read_yaml(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def gzip_str(string: str, encoding='utf-8') -> bytes:
    out = BytesIO()

    with GzipFile(fileobj=out, mode='w') as f:
        f.write(string.encode(encoding))

    return out.getvalue()


def extract_gzip(body: bytes, encoding='utf-8') -> str:
    with GzipFile(fileobj=BytesIO(body), mode='r') as f:
        return f.read().decode(encoding)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def reverse_timestamp(date: datetime) -> str:
    """
    Returns a string representing `datetime.max - date` in seconds.

    This ensures the following relation:
        `date_1 >= date_2` iff `reverse_timestamp(date_1) <= reverse_timestamp(date_2)`
    """
    date_max = datetime.max.replace(tzinfo=timezone.utc)
    return str(int((date_max - date).total_seconds()))


def emptystr_to_none(item):
    """
    Replace empty strings with `None` recursively inside a JSON-like object.
    """
    if isinstance(item, list):
        return list(map(emptystr_to_none, item))
    if isinstance(item, dict):
        return valmap(emptystr_to_none, item)
    else:
        return None if item == "" else item
