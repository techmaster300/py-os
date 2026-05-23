import json
import os
from translation import detect_system_lang

CONFIG_FILE = "pyos_config.json"

def get_config_path(data_dir):
    return os.path.join(data_dir, CONFIG_FILE)

DEFAULT_LANG = detect_system_lang()

def load_config(data_dir):
    path = get_config_path(data_dir)
    default = {"developer_mode": False, "language": DEFAULT_LANG}
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default

def save_config(data_dir, config):
    path = get_config_path(data_dir)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)

APPEARANCE_FILE = "appearance_config.json"

def get_appearance_path(data_dir):
    return os.path.join(data_dir, APPEARANCE_FILE)

def load_appearance_config(data_dir):
    path = get_appearance_path(data_dir)
    defaults = {
        "desktop_bg": "#000000",
        "desktop_button_bg": "#282828",
        "desktop_button_fg": "#FFFFFF",
        "desktop_header": "PyOS Desktop",
        "desktop_header_color": "#FFFFFF",
        "desktop_header_font_size": 18,
        "desktop_button_font_size": 16,
        "desktop_button_spacing": 5,
        "desktop_greeting": "Welcome to PyOS. Use Tab to navigate through apps, and press Enter to launch.",
        "desktop_scroll_rate": 20,
        "desktop_width": 800,
        "desktop_height": 600,
        "lockscreen_bg": "#000000",
        "lockscreen_title_color": "#FFFFFF",
        "lockscreen_title_text": "Lock Screen",
        "lockscreen_title_font_size": 18,
        "lockscreen_mode_color": "#B4B4B4",
        "lockscreen_status_color": "#FF5050",
        "lockscreen_input_bg": "#1E1E1E",
        "lockscreen_input_fg": "#FFFFFF",
        "lockscreen_display_font_size": 20,
        "lockscreen_input_font_size": 14,
        "lockscreen_pin_font_size": 14,
        "lockscreen_mask_char": "*",
        "lockscreen_width": 350,
        "lockscreen_height": 460,
    }
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r") as f:
            loaded = json.load(f)
            defaults.update(loaded)
            return defaults
    except Exception:
        return defaults

def save_appearance_config(data_dir, config):
    path = get_appearance_path(data_dir)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
