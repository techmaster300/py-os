import json
import os

SLOT_FILE = "slot_state.json"

def get_slot_path(data_dir):
    return os.path.join(data_dir, SLOT_FILE)

def load_state(data_dir):
    path = get_slot_path(data_dir)
    default = {"active_slot": "a", "boot_successful": True, "boot_count": 0}
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return {**default, **json.load(f)}
    except Exception:
        return default

def save_state(data_dir, state):
    path = get_slot_path(data_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)

def mark_boot_attempt(data_dir):
    state = load_state(data_dir)
    state["boot_count"] = state.get("boot_count", 0) + 1
    state["boot_successful"] = False
    save_state(data_dir, state)
    return state["active_slot"]

def mark_boot_success(data_dir):
    state = load_state(data_dir)
    state["boot_successful"] = True
    state["boot_count"] = 0
    save_state(data_dir, state)

def switch_slot(data_dir):
    state = load_state(data_dir)
    state["active_slot"] = "b" if state.get("active_slot") == "a" else "a"
    state["boot_successful"] = False
    state["boot_count"] = 0
    save_state(data_dir, state)
    return state["active_slot"]

def get_active_slot(data_dir):
    return load_state(data_dir).get("active_slot", "a")

def should_fallback(data_dir):
    state = load_state(data_dir)
    return state["boot_count"] >= 2 and not state["boot_successful"]
