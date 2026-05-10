import subprocess
import threading
import json
import os
import time

class SoundManager:
    def __init__(self, data_dir):
        # Normalize the path initially
        self.data_dir = os.path.normpath(data_dir)
        print(f"Normalized data_dir: {repr(self.data_dir)}")

        # Paths for configuration and custom themes
        self.config_path = os.path.join(self.data_dir, "sound_theme.json")
        self.custom_themes_dir = os.path.join(self.data_dir, "themes")
        print(f"Custom themes directory: {repr(self.custom_themes_dir)}")

        # Default themes are hardcoded
        self.default_themes = {
            "Modern": {
                "startup": [(349, 150), (440, 150), (523, 150), (698, 300)],
                "nav": [(600, 50)],
                "launch": [(440, 100), (880, 100)],
                "close": [(880, 100), (440, 100)],
                "alert": [(1000, 200), (800, 200)]
            },
            "Retro": {
                "startup": [(100, 100), (200, 100), (300, 100)],
                "nav": [(150, 30)],
                "launch": [(200, 50), (400, 50), (600, 50)],
                "close": [(600, 50), (400, 50), (200, 50)],
                "alert": [(400, 100), (400, 100), (400, 100)]
            },
            "Classic": {
                "startup": [(523, 400)],
                "nav": [(400, 20)],
                "launch": [(523, 100)],
                "close": [(261, 100)],
                "alert": [(1000, 500)]
            }
        }
        self.themes = self.default_themes.copy()

        # Load custom themes and merge them
        custom_themes_data = self._load_all_custom_themes()
        self.themes.update(custom_themes_data)

        self.current_theme = self.load_theme_name()

    def _load_all_custom_themes(self):
        """Loads all custom themes from the theme directory."""
        if not os.path.exists(self.custom_themes_dir):
            os.makedirs(self.custom_themes_dir)
            return {}

        custom_themes_data = {}
        for item in os.listdir(self.custom_themes_dir):
            theme_dir = os.path.join(self.custom_themes_dir, item)
            if os.path.isdir(theme_dir):
                theme_name = item
                theme_config_path = os.path.join(theme_dir, 'theme.json')
                if os.path.exists(theme_config_path):
                    try:
                        with open(theme_config_path, "r", encoding='utf-8') as f:
                            theme_config = json.load(f)
                            custom_themes_data[theme_name] = theme_config
                    except Exception as e:
                        print(f"Warning: Error loading theme config from {theme_config_path}: {e}")
        return custom_themes_data

    def save_custom_themes(self):
        """Saves all custom themes to their respective directories."""
        if not os.path.exists(self.custom_themes_dir):
            os.makedirs(self.custom_themes_dir)

        for theme_name, theme_data in self.themes.items():
            if theme_name not in self.default_themes:
                theme_dir = os.path.join(self.custom_themes_dir, theme_name)
                os.makedirs(theme_dir, exist_ok=True)
                theme_config_path = os.path.join(theme_dir, 'theme.json')
                try:
                    with open(theme_config_path, "w", encoding='utf-8') as f:
                        json.dump(theme_data, f, indent=4)
                except Exception as e:
                    print(f"Error saving custom theme '{theme_name}': {e}")

    def load_theme_name(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    config_data = json.load(f)
                    theme_name = config_data.get("theme", "Modern")
                    if theme_name not in self.themes:
                        return "Modern"
                    return theme_name
            except Exception:
                return "Modern"
        return "Modern"

    def save_theme_name(self, name):
        if name in self.themes:
            self.current_theme = name
            try:
                with open(self.config_path, "w", encoding='utf-8') as f:
                    json.dump({"theme": name}, f)
            except Exception as e:
                print(f"Error saving theme name: {e}")

    def play(self, sound_type):
        if self.current_theme not in self.themes:
            self.current_theme = "Modern"

        theme_data = self.themes.get(self.current_theme, self.themes["Modern"])
        data = theme_data.get(sound_type)
        if not data: return

        # Startup sound is synchronous
        if sound_type == "startup":
            if isinstance(data, str):
                self._play_file_sync(data)
            else:
                self._play_notes_sync(data)
        else:
            if isinstance(data, str):
                threading.Thread(target=self._play_file, args=(data,), daemon=True).start()
            else:
                threading.Thread(target=self._play_notes, args=(data,), daemon=True).start()

    def _play_notes(self, notes):
        """Play a sequence of notes using ffplay and lavfi."""
        filter_str = self._build_notes_filter(notes)
        if filter_str:
            try:
                # -nodisp: don't show display
                # -autoexit: exit after playing
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-f", "lavfi", filter_str], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing notes: {e}")

    def _play_notes_sync(self, notes):
        """Play notes synchronously."""
        filter_str = self._build_notes_filter(notes)
        if filter_str:
            try:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-f", "lavfi", filter_str], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing notes sync: {e}")

    def _build_notes_filter(self, notes):
        """Builds a lavfi filter string for a sequence of sine waves."""
        if not notes: return None
        
        parts = []
        for i, (freq, dur) in enumerate(notes):
            dur_sec = dur / 1000.0
            parts.append(f"sine=f={freq}:d={dur_sec}[v{i}]")
        
        # Concat all sine waves
        inputs = "".join([f"[v{i}]" for i in range(len(notes))])
        concat = f"{inputs}concat=n={len(notes)}:v=0:a=1[out]"
        
        return ";".join(parts) + ";" + concat

    def _play_file(self, path):
        if os.path.exists(path):
            try:
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", path], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing file: {e}")

    def _play_file_sync(self, path):
        if os.path.exists(path):
            try:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", path], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing file sync: {e}")

    def get_available_themes(self):
        return list(self.themes.keys())
