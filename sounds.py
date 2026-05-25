import subprocess
import threading
import json
import os
import time
import audio_devices

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

class SoundManager:
    def __init__(self, data_dir):
        self.data_dir = os.path.normpath(data_dir)
        self.config_path = os.path.join(self.data_dir, "sound_theme.json")
        self.custom_themes_dir = os.path.join(self.data_dir, "themes")
        self.volume = 1.0

        # Default themes are hardcoded
        self.default_themes = {
            "Modern": {
                "startup": [(349, 150), (440, 150), (523, 150), (698, 300)],
                "nav": [(600, 50)],
                "launch": [(440, 100), (880, 100)],
                "close": [(880, 100), (440, 100)],
                "alert": [(1000, 200), (800, 200)],
                "shutdown": [(659, 200), (523, 200), (392, 300)],
                "power_menu": [(440, 80)],
                "context_menu": [(400, 50)],
                "notify": [(698, 100), (880, 100)],
                "logon": [(523, 200), (659, 200), (784, 300)],
                "logoff": [(784, 200), (659, 200), (523, 300)],
                "error": [(1000, 400), (800, 400)],
                "alarm": [(1000, 100), (0, 100), (1000, 100), (0, 100)],
                "timer": [(880, 80)],
                "info": [(523, 100)],
                "complete": [(523, 100), (659, 100), (784, 200)],
                "device_connect": [(440, 80), (659, 80)],
                "device_disconnect": [(659, 80), (440, 80)]
            },
            "Retro": {
                "startup": [(100, 100), (200, 100), (300, 100)],
                "nav": [(150, 30)],
                "launch": [(200, 50), (400, 50), (600, 50)],
                "close": [(600, 50), (400, 50), (200, 50)],
                "alert": [(400, 100), (400, 100), (400, 100)],
                "shutdown": [(300, 100), (200, 100), (100, 200)],
                "power_menu": [(200, 30)],
                "context_menu": [(150, 20)],
                "notify": [(300, 50), (400, 50)],
                "logon": [(200, 80), (300, 80), (400, 100)],
                "logoff": [(400, 80), (300, 80), (200, 100)],
                "error": [(500, 100), (500, 100)],
                "alarm": [(600, 60), (0, 60), (600, 60), (0, 60)],
                "timer": [(300, 40)],
                "info": [(400, 50)],
                "complete": [(300, 60), (400, 60), (500, 100)],
                "device_connect": [(300, 50), (500, 50)],
                "device_disconnect": [(500, 50), (300, 50)]
            },
            "Classic": {
                "startup": [(523, 400)],
                "nav": [(400, 20)],
                "launch": [(523, 100)],
                "close": [(261, 100)],
                "alert": [(1000, 500)],
                "shutdown": [(392, 300)],
                "power_menu": [(400, 50)],
                "context_menu": [(440, 30)],
                "notify": [(440, 60), (659, 60)],
                "logon": [(523, 300)],
                "logoff": [(392, 300)],
                "error": [(800, 600)],
                "alarm": [(1000, 80), (0, 80), (1000, 80)],
                "timer": [(659, 50)],
                "info": [(659, 60)],
                "complete": [(523, 100), (659, 100), (784, 200)],
                "device_connect": [(440, 60), (659, 60)],
                "device_disconnect": [(659, 60), (440, 60)]
            },
            "Windows XP": {}
        }
        
        # Resolve Windows XP sound file paths relative to this file's location
        xp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", "xp")
        if os.path.isdir(xp_dir):
            self.default_themes["Windows XP"] = {
                "startup": os.path.join(xp_dir, "Windows XP Startup.wav"),
                "nav": os.path.join(xp_dir, "Windows XP Menu Command.wav"),
                "launch": os.path.join(xp_dir, "Windows XP Default.wav"),
                "close": os.path.join(xp_dir, "Windows XP Recycle.wav"),
                "alert": os.path.join(xp_dir, "Windows XP Exclamation.wav"),
                "shutdown": os.path.join(xp_dir, "Windows XP Shutdown.wav"),
                "power_menu": os.path.join(xp_dir, "Windows XP Start.wav"),
                "context_menu": os.path.join(xp_dir, "Windows XP Menu Command.wav"),
                "notify": os.path.join(xp_dir, "Windows XP Notify.wav"),
                "logon": os.path.join(xp_dir, "Windows XP Logon Sound.wav"),
                "logoff": os.path.join(xp_dir, "Windows XP Logoff Sound.wav"),
                "error": os.path.join(xp_dir, "Windows XP Critical Stop.wav"),
                "alarm": os.path.join(xp_dir, "Windows XP Critical Stop.wav"),
                "timer": os.path.join(xp_dir, "Windows XP Menu Command.wav"),
                "info": os.path.join(xp_dir, "Windows XP Information Bar.wav"),
                "complete": os.path.join(xp_dir, "tada.wav"),
                "device_connect": os.path.join(xp_dir, "Windows XP Hardware Insert.wav"),
                "device_disconnect": os.path.join(xp_dir, "Windows XP Hardware Remove.wav")
            }

        self.themes = self.default_themes.copy()
        custom_themes_data = self._load_all_custom_themes()
        self.themes.update(custom_themes_data)
        self.current_theme = self.load_theme_name()
        
        # Improved cache
        self._audio_cache = {}
        # Preload essential sounds (best-effort, non-fatal)
        try:
            self.preload_sounds(["nav", "launch", "close", "alert"])
        except Exception:
            pass

        # Whether to force ffplay (for debugging/custom setups)
        self._use_ffmpeg = self._load_ffmpeg_flag()

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, float(volume)))

    def preload_sounds(self, sound_types):
        """Preload commonly used sounds into the cache."""
        theme_data = self.themes.get(self.current_theme, self.themes["Modern"])
        for st in sound_types:
            data = theme_data.get(st)
            if isinstance(data, str):
                self._get_cached_audio(data)

    # ... (rest of the class)

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

    def get_ffmpeg_flag(self):
        return self._use_ffmpeg

    def set_ffmpeg_flag(self, enabled):
        self._use_ffmpeg = bool(enabled)
        try:
            cfg = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding='utf-8') as f:
                    cfg = json.load(f)
            cfg["use_ffmpeg"] = self._use_ffmpeg
            with open(self.config_path, "w", encoding='utf-8') as f:
                json.dump(cfg, f, indent=4)
        except Exception as e:
            print(f"Error saving ffmpeg flag: {e}")

    def _load_ffmpeg_flag(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding='utf-8') as f:
                    return bool(json.load(f).get("use_ffmpeg", False))
            except Exception:
                pass
        return False

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

    def preview(self, data):
        if isinstance(data, str):
            self._play_file_sync(data)
        else:
            self._play_notes_sync(data)

    def _play_notes(self, notes):
        """Play a sequence of notes — sounddevice primary, ffplay fallback."""
        if not self._use_ffmpeg and self._play_notes_with_sounddevice(notes):
            return
        self._play_notes_ffplay(notes)

    def _play_notes_sync(self, notes):
        """Play notes synchronously — sounddevice primary, ffplay fallback."""
        if not self._use_ffmpeg and self._play_notes_with_sounddevice(notes):
            return
        self._play_notes_ffplay(notes)

    def _build_notes_filter(self, notes):
        """Builds a lavfi filter string for a sequence of sine waves."""
        if not notes: return None
        
        parts = []
        for i, (freq, dur) in enumerate(notes):
            dur_sec = dur / 1000.0
            parts.append(f"sine=f={freq}:d={dur_sec}[v{i}]")
        
        # Concat all sine waves and add a small pad
        inputs = "".join([f"[v{i}]" for i in range(len(notes))])
        concat = f"{inputs}concat=n={len(notes)}:v=0:a=1,apad=pad_dur=0.3[out]"
        
        return ";".join(parts) + ";" + concat

    def _play_file(self, path):
        if os.path.exists(path):
            if not self._use_ffmpeg and self._play_file_with_sounddevice(path):
                return
            try:
                clean_path = path.replace(os.sep, '/')
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-af", "apad=pad_dur=0.3", clean_path], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing file: {e}")

    def _play_file_sync(self, path):
        if os.path.exists(path):
            if not self._use_ffmpeg and self._play_file_with_sounddevice(path):
                return
            try:
                clean_path = path.replace(os.sep, '/')
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-af", "apad=pad_dur=0.3", clean_path], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing file sync: {e}")

    def _selected_output_device_index(self):
        config = audio_devices.load_device_config(self.data_dir)
        outputs = audio_devices.list_output_devices()
        return audio_devices.resolve_selected_index(
            outputs, config, "output_device_index", "output_device"
        )

    def _play_notes_with_sounddevice(self, notes):
        if not HAS_SOUNDDEVICE or not HAS_NUMPY or not notes:
            return False
        try:
            sample_rate = 44100
            parts = []
            for freq, dur in notes:
                duration_seconds = max(dur, 1) / 1000.0
                t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), endpoint=False, dtype=np.float32)
                wave = 0.20 * np.sin(2 * np.pi * float(freq) * t)
                parts.append(wave)
            audio = np.concatenate(parts) if parts else np.array([], dtype=np.float32)
            if audio.size == 0:
                return False
            # Add 300ms silence padding so tones don't feel cut off
            pad_samples = int(sample_rate * 0.3)
            audio = np.concatenate([audio, np.zeros(pad_samples, dtype=np.float32)])
            device_index = self._selected_output_device_index()
            sd.play(audio, samplerate=sample_rate, device=device_index, blocking=True)
            return True
        except Exception as e:
            print(f"Sounddevice notes playback failed, falling back to ffplay: {e}")
            return False

    def _play_file_with_sounddevice(self, path):
        if not HAS_SOUNDDEVICE or not HAS_NUMPY:
            return False
        try:
            audio, sample_rate = self._get_cached_audio(path)
            if isinstance(audio, np.ndarray) and audio.size == 0:
                return False
            # Add 300ms silence padding so sounds don't feel cut off
            pad_samples = int(sample_rate * 0.3)
            pad_shape = (pad_samples, audio.shape[1]) if audio.ndim == 2 else (pad_samples,)
            audio = np.concatenate([audio, np.zeros(pad_shape, dtype=np.float32)])
            device_index = self._selected_output_device_index()
            sd.play(audio, samplerate=sample_rate, device=device_index, blocking=True)
            return True
        except Exception as e:
            print(f"Sounddevice file playback failed, falling back to ffplay: {e}")
            return False

    def _get_cached_audio(self, path):
        if not HAS_SOUNDFILE or not HAS_NUMPY:
            raise RuntimeError("soundfile and numpy required for file playback")
        abs_path = os.path.abspath(path)
        mtime = os.path.getmtime(abs_path)
        cached = self._audio_cache.get(abs_path)
        if cached and cached.get("mtime") == mtime:
            return cached["audio"], cached["rate"]
        audio, sample_rate = sf.read(abs_path, dtype="float32", always_2d=False)
        self._audio_cache[abs_path] = {
            "mtime": mtime,
            "audio": audio,
            "rate": sample_rate,
        }
        return audio, sample_rate

    def _play_notes_ffplay(self, notes):
        filter_str = self._build_notes_filter(notes)
        if filter_str:
            try:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-f", "lavfi", filter_str],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"Error playing notes: {e}")

    def get_available_themes(self):
        return list(self.themes.keys())
