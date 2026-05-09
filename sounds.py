import winsound
import threading
import json
import os

class SoundManager:
    def __init__(self, data_dir):
        self.data_dir = os.path.normpath(data_dir) # Normalize the path
        self.data_dir = os.path.normpath(data_dir) # Normalize the path
        self.data_dir = self.data_dir.replace('\\', '/') # Ensure forward slashes for consistency
        print(f"Normalized data_dir: {repr(self.data_dir)}") # Print normalized path
        self.config_path = os.path.join(self.data_dir, "sound_theme.json")
        self.user_themes_path = self.data_dir + "/user_themes.json" # Path for custom themes, forcing forward slashes
        print(f"User themes path: {repr(self.user_themes_path)}") # Print the final constructed path

        self.themes = {
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

        # Load custom themes and merge them with default themes
        custom_themes = self.load_custom_themes()
        self.themes.update(custom_themes)

        self.current_theme = self.load_theme_name()

    def load_custom_themes(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if os.path.exists(self.user_themes_path):
            try:
                with open(self.user_themes_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON from {self.user_themes_path}. Using default themes.")
                return {}
            except Exception as e:
                print(f"Warning: Error loading custom themes from {self.user_themes_path}: {e}")
                return {}
        return {}

    def save_custom_themes(self):
        # Save all current themes (default and custom) to user_themes.json
        # This ensures that all themes, including any newly created ones, are persisted.
        try:
            with open(self.user_themes_path, "w") as f:
                json.dump(self.themes, f, indent=4) # Use indent for readability
        except Exception as e:
            print(f"Error saving custom themes to {self.user_themes_path}: {e}")

    def load_theme_name(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    theme_name = json.load(f).get("theme", "Modern")
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
                with open(self.config_path, "w") as f:
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

        if isinstance(data, str):
            # It's a file path
            threading.Thread(target=self._play_file, args=(data,), daemon=True).start()
        else:
            # It's a list of frequencies
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
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e: 
                print(f"Error playing sound file {path}: {e}")
        else:
            print(f"Sound file not found: {path}")

    def get_available_themes(self):
        return list(self.themes.keys())
