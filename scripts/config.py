import os, json


def load_config(path) -> dict:
    
    config = {}
    config_paths = os.listdir(path)
    
    for current_path in config_paths:
        if current_path[-12:] == "_config.json":
            with open(f"{path}/{current_path}") as file:
                current_config = json.load(file)
            config[current_path[:-12]] = current_config
        
    return config