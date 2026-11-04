import json
from pathlib import Path


def load_config(path):
    config = {}
    for file in sorted(Path(path).glob('*_config.json')):
        with file.open(encoding='utf-8') as source:
            config[file.name[:-12]] = json.load(source)
    return config
