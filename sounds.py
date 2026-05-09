import winsound
import threading
import json
import os

class SoundManager:
    def __init__(self, data_dir):
        # Normalize the path initially
        self.data_dir = os.path.normpath(data_dir)
        # Removed problematic line: self.data_dir = self.data_dir.replace(os.sep, '/') 
        # Relying on os.path.normpath for correct path handling.
        print(f"Normalized data_dir: {repr(self.data_dir)}")

        # Paths for configuration and custom themes
        self.config_path = os.path.join(self.data_dir, "sound_theme.json")
        self.custom_themes_dir = os.path.join(self.data_dir, "themes") # New directory for custom themes
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
        self.themes = self.default_themes.copy() # Initialize with default themes

        # Load custom themes and merge them
        custom_themes_data = self._load_all_custom_themes()
        self.themes.update(custom_themes_data)

        self.current_theme = self.load_theme_name()

    def _load_all_custom_themes(self):
        """Loads all custom themes from the theme directory."""
        if not os.path.exists(self.custom_themes_dir):
            os.makedirs(self.custom_themes_dir)
            return {} # Return empty if directory doesn't exist yet

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
                            # Ensure file paths within theme_config are handled correctly
                            # (e.g., making them absolute or relative to the theme directory)
                            # For simplicity now, assume paths are absolute or correctly resolvable.
                            custom_themes_data[theme_name] = theme_config
                    except json.JSONDecodeError:
                        print(f"Warning: Could not decode JSON from {theme_config_path}. Skipping theme '{theme_name}'.")
                    except Exception as e:
                        print(f"Warning: Error loading theme config from {theme_config_path}: {e}. Skipping theme '{theme_name}'.")
        return custom_themes_data

    def save_custom_themes(self):
        """Saves all custom themes to their respective directories."""
        if not os.path.exists(self.custom_themes_dir):
            os.makedirs(self.custom_themes_dir)

        for theme_name, theme_data in self.themes.items():
            # Only save themes that are not default themes.
            if theme_name not in self.default_themes:
                theme_dir = os.path.join(self.custom_themes_dir, theme_name)
                os.makedirs(theme_dir, exist_ok=True) # Create directory if it doesn't exist
                theme_config_path = os.path.join(theme_dir, 'theme.json')
                try:
                    with open(theme_config_path, "w", encoding='utf-8') as f:
                        json.dump(theme_data, f, indent=4) # Use indent for readability
                except Exception as e:
                    print(f"Error saving custom theme '{theme_name}' to {theme_config_path}: {e}")

    def load_theme_name(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    config_data = json.load(f)
                    theme_name = config_data.get("theme", "Modern")
                    # Ensure the loaded theme name is valid
                    if theme_name not in self.themes:
                        print(f"Warning: Theme '{theme_name}' not found. Reverting to 'Modern'.")
                        return "Modern"
                    return theme_name
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {self.config_path}. Reverting to 'Modern'.")
                return "Modern"
            except Exception as e:
                print(f"Warning: Error loading theme name from {self.config_path}: {e}. Reverting to 'Modern'.")
                return "Modern"
        return "Modern"

    def save_theme_name(self, name):
        if name in self.themes:
            self.current_theme = name
            try:
                with open(self.config_path, "w", encoding='utf-8') as f:
                    json.dump({"theme": name}, f)
            except Exception as e:
                print(f"Error saving theme name to {self.config_path}: {e}")
        else:
            print(f"Warning: Theme '{name}' does not exist and cannot be saved.")

    def play(self, sound_type):
        # Ensure current_theme is valid, otherwise fallback to Modern
        if self.current_theme not in self.themes:
            print(f"Warning: Current theme '{self.current_theme}' is invalid. Falling back to 'Modern'.")
            self.current_theme = "Modern"
            self.save_theme_name("Modern") # Save the fallback

        theme_data = self.themes.get(self.current_theme, self.themes["Modern"])
        data = theme_data.get(sound_type)
        if not data: return

        # --- Modification for synchronous startup sound ---
        if sound_type == "startup": # Make startup sound synchronous
            if isinstance(data, str):
                self._play_file_sync(data) # Use a synchronous file player
            else:
                self._play_notes_sync(data) # Play tones synchronously
        else: # For all other sounds, continue playing asynchronously
            if isinstance(data, str):
                threading.Thread(target=self._play_file, args=(data,), daemon=True).start()
            else:
                threading.Thread(target=self._play_notes, args=(data,), daemon=True).start()

    def _play_notes(self, notes):
        for freq, dur in notes:
            try:
                winsound.Beep(freq, dur)
            except Exception as e: 
                print(f"Error playing beep: {e}")

    def _play_file(self, path):
        if os.path.exists(path):
            try:
                # winsound.PlaySound only supports .wav files
                # SND_ASYNC plays the sound asynchronously, so the thread returns immediately
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e: 
                print(f"Error playing sound file {path}: {e}")
        else:
            print(f"Sound file not found: {path}")

    # New synchronous playback methods for notes and files
    def _play_notes_sync(self, notes):
        for freq, dur in notes:
            try:
                winsound.Beep(freq, dur)
            except Exception as e: 
                print(f"Error playing beep synchronously: {e}")

    def _play_file_sync(self, path):
        if os.path.exists(path):
            try:
                # winsound.PlaySound without SND_ASYNC plays synchronously
                winsound.PlaySound(path, winsound.SND_FILENAME)
            except Exception as e: 
                print(f"Error playing sound file synchronously: {e}")
        else:
            print(f"Sound file not found: {path}")

    def get_available_themes(self):
        return list(self.themes.keys())
