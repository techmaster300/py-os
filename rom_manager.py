import json
import os
import shutil
import zipfile

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
    "accent_color": "#00B4FF",
    "boot_logo": "PyOS",
    "boot_logo_color": "#00B4FF",
}

def get_roms_dir(data_dir):
    return os.path.join(data_dir, ROMS_DIR)

def get_active_rom_path(data_dir):
    return os.path.join(data_dir, ACTIVE_ROM_FILE)

def list_roms(data_dir):
    roms = [("Stock", dict(STOCK_ROM))]
    roms_dir = get_roms_dir(data_dir)
    if os.path.isdir(roms_dir):
        for entry in sorted(os.listdir(roms_dir)):
            manifest = os.path.join(roms_dir, entry, "rom.json")
            if os.path.isfile(manifest):
                try:
                    with open(manifest) as f:
                        data = json.load(f)
                        roms.append((entry, data))
                except Exception:
                    pass
    return roms

def get_rom(data_dir, name):
    for rname, rdata in list_roms(data_dir):
        if rname == name:
            return rdata
    return None

def get_active_rom(data_dir):
    path = get_active_rom_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path) as f:
                name = json.load(f).get("rom", "Stock")
                r = get_rom(data_dir, name)
                if r:
                    return name, r
        except Exception:
            pass
    return "Stock", dict(STOCK_ROM)

def set_active_rom(data_dir, name):
    path = get_active_rom_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"rom": name}, f)

def delete_rom(data_dir, name):
    if name == "Stock":
        return False
    rom_dir = os.path.join(get_roms_dir(data_dir), name)
    if os.path.isdir(rom_dir):
        shutil.rmtree(rom_dir)
        return True
    return False

def install_rom(data_dir, source_path):
    if not os.path.exists(source_path):
        return None
    base = get_roms_dir(data_dir)
    os.makedirs(base, exist_ok=True)
    if source_path.endswith(".zip"):
        with zipfile.ZipFile(source_path) as z:
            if "rom.json" not in z.namelist():
                return None
            z.extractall(base)
            rom_name = os.path.basename(source_path).replace(".zip", "")
            dest = os.path.join(base, rom_name)
            if not os.path.isdir(dest):
                os.rename(os.path.join(base, "rom.json"), os.path.join(base, rom_name, "rom.json"))
            with open(os.path.join(dest, "rom.json")) as f:
                data = json.load(f)
            return data.get("name", rom_name)
    elif source_path.endswith(".json"):
        with open(source_path) as f:
            data = json.load(f)
        rom_name = data.get("name", os.path.basename(source_path).replace(".json", ""))
        dest = os.path.join(base, rom_name)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(source_path, os.path.join(dest, "rom.json"))
        return rom_name
    return None

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

def export_current_config(data_dir, export_path):
    ac_path = os.path.join(data_dir, "appearance_config.json")
    st_path = os.path.join(data_dir, "sound_theme.json")
    ac = {}
    if os.path.exists(ac_path):
        with open(ac_path) as f:
            ac = json.load(f)
    sound_theme = "Modern"
    if os.path.exists(st_path):
        with open(st_path) as f:
            sound_theme = json.load(f).get("theme", "Modern")
    rom = {
        "name": ac.get("desktop_header", "PyOS Desktop").replace(" ", ""),
        "version": "1.0",
        "author": "User",
        "description": "Exported from current config",
        "sound_theme": sound_theme,
        "wallpaper_path": ac.get("wallpaper_path", ""),
        "wallpaper_style": ac.get("wallpaper_style", "stretch"),
        "header": ac.get("desktop_header", "PyOS Desktop"),
        "header_color": ac.get("desktop_header_color", "#FFFFFF"),
        "bg_color": ac.get("desktop_bg", "#000000"),
        "button_bg": ac.get("desktop_button_bg", "#282828"),
        "button_fg": ac.get("desktop_button_fg", "#FFFFFF"),
        "accent_color": "#00B4FF",
        "boot_logo": "PyOS",
        "boot_logo_color": "#00B4FF",
    }
    with open(export_path, "w") as f:
        json.dump(rom, f, indent=2)
