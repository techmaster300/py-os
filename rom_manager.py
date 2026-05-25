import json
import os
import shutil

ROMS_DIR = "roms"
ACTIVE_ROM_FILE = "active_rom.json"

STOCK_ROM = {
    "name": "Stock",
    "version": "1.0",
    "author": "PyOS",
    "description": "Default PyOS experience",
    "sound_theme": "Modern",
    "wallpaper_path": "",
    "wallpaper_style": "stretch",
    "header": "PyOS Desktop",
    "header_color": "#FFFFFF",
    "bg_color": "#000000",
    "button_bg": "#282828",
    "button_fg": "#FFFFFF",
}

def get_roms_dir(data_dir):
    return os.path.join(data_dir, ROMS_DIR)

def get_active_rom_path(data_dir):
    return os.path.join(data_dir, ACTIVE_ROM_FILE)

def list_roms(data_dir):
    roms = [("Stock", STOCK_ROM)]
    roms_dir = get_roms_dir(data_dir)
    if os.path.isdir(roms_dir):
        for entry in os.listdir(roms_dir):
            manifest = os.path.join(roms_dir, entry, "rom.json")
            if os.path.isfile(manifest):
                try:
                    with open(manifest) as f:
                        data = json.load(f)
                        roms.append((entry, data))
                except Exception:
                    pass
    return roms

def get_active_rom(data_dir):
    path = get_active_rom_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path) as f:
                name = json.load(f).get("rom", "Stock")
                for rname, rdata in list_roms(data_dir):
                    if rname == name:
                        return rname, rdata
        except Exception:
            pass
    return "Stock", STOCK_ROM

def set_active_rom(data_dir, name):
    path = get_active_rom_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"rom": name}, f)

def apply_rom_config(data_dir):
    name, rom = get_active_rom(data_dir)
    ac_path = os.path.join(data_dir, "appearance_config.json")
    if os.path.exists(ac_path):
        try:
            with open(ac_path) as f:
                ac = json.load(f)
        except Exception:
            ac = {}
    else:
        ac = {}
    ac["desktop_header"] = rom.get("header", "PyOS Desktop")
    ac["desktop_header_color"] = rom.get("header_color", "#FFFFFF")
    ac["desktop_bg"] = rom.get("bg_color", "#000000")
    ac["desktop_button_bg"] = rom.get("button_bg", "#282828")
    ac["desktop_button_fg"] = rom.get("button_fg", "#FFFFFF")
    ac["wallpaper_path"] = rom.get("wallpaper_path", "")
    ac["wallpaper_style"] = rom.get("wallpaper_style", "stretch")
    os.makedirs(os.path.dirname(ac_path), exist_ok=True)
    with open(ac_path, "w") as f:
        json.dump(ac, f, indent=2)
    st_path = os.path.join(data_dir, "sound_theme.json")
    st = {"theme": rom.get("sound_theme", "Modern")}
    with open(st_path, "w") as f:
        json.dump(st, f, indent=2)
