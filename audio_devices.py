import json
import os

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


def get_device_config_path(data_dir):
    return os.path.join(data_dir, "device_config.json")


def load_device_config(data_dir):
    path = get_device_config_path(data_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_device_config(data_dir, input_choice, output_choice):
    config = {
        "input_device": input_choice.get("name", "Default"),
        "output_device": output_choice.get("name", "Default"),
        "input_device_index": input_choice.get("index"),
        "output_device_index": output_choice.get("index")
    }
    path = get_device_config_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def list_input_devices():
    if not HAS_SOUNDDEVICE:
        return []
    devices = sd.query_devices()
    results = []
    seen_names = set()
    for idx, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            name = str(d.get("name", f"Input Device {idx}")).strip()
            key = " ".join(name.lower().split())
            if key in seen_names:
                continue
            seen_names.add(key)
            results.append({"index": idx, "name": name})
    return results


def list_output_devices():
    if not HAS_SOUNDDEVICE:
        return []
    devices = sd.query_devices()
    results = []
    seen_names = set()
    for idx, d in enumerate(devices):
        if d.get("max_output_channels", 0) > 0:
            name = str(d.get("name", f"Output Device {idx}")).strip()
            key = " ".join(name.lower().split())
            if key in seen_names:
                continue
            seen_names.add(key)
            results.append({"index": idx, "name": name})
    return results

def is_device_valid(device_index):
    """Checks if a device index is currently valid."""
    if not HAS_SOUNDDEVICE:
        return False
    try:
        devices = sd.query_devices()
        return 0 <= device_index < len(devices)
    except Exception:
        return False

def resolve_selected_index(entries, config, index_key, name_key):
    cfg_index = config.get(index_key)
    # Check if index is still valid
    if isinstance(cfg_index, int) and is_device_valid(cfg_index):
        return cfg_index
    
    cfg_name = config.get(name_key)
    if isinstance(cfg_name, str):
        for e in entries:
            if e["name"] == cfg_name:
                return e["index"]
    return None
