import json, os
from config import *

SETTINGS_FILE = "settings.json"

def load_settings():
    """Load settings từ file JSON, nếu không có thì lấy mặc định từ config.py"""
    defaults = {k: v for k, v in globals().items() if k.isupper() and not k.startswith('_')}
    
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(defaults, f, indent=4)
        return defaults
    
    with open(SETTINGS_FILE, "r") as f:
        return {**defaults, **json.load(f)}

def save_setting(key, value):
    """Cập nhật giá trị vào file JSON"""
    if not os.path.exists(SETTINGS_FILE):
        settings = {}
    else:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    
    settings[key] = value
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)