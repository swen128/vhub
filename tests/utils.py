import json

import yaml


def read_file(path: str) -> str:
    with open(path, 'r') as f:
        return f.read()


def read_json(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)


def read_yaml(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)
