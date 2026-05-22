import wx
import os
import datetime
import subprocess
import speech
from api import BlindApp
import audio_devices

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

class SettingsApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "System Settings"
        self.description = "Configure tts, audio devices, updates, and more."
        self.help_text = "Use Tab to navigate controls, and Enter to save."
        self.docs = "Settings allows you to customize the OS behavior. Voice speed can be adjusted from 50 to 400. Configure audio input and output devices."
        self.device_config_path = self.api.get_data_path("device_config.json")
        self.input_entries = []
        self.output_entries = []
        self.easter_egg_count = 0

    def get_input_devices(self):
        if not HAS_SOUNDDEVICE: return []
        devices = sd.query_devices()
        return [d for d in devices if d['max_input_channels'] > 0]

    def get_output_devices(self):
        if not HAS_SOUNDDEVICE: return []
        devices = sd.query_devices()
        return [d for d in devices if d['max_output_channels'] > 0]

    def _device_label(self, device):
        return f"{device['name']} ({device['hostapi']})"

    def load_device_config(self):
        if not os.path.exists(self.device_config_path): return {}
        try:
            import json
            with open(self.device_config_path, "r") as f: return json.load(f)
        except: return {}

    def save_device_config(self, input_device, output_device):
        try:
            audio_devices.save_device_config(self.api.data_dir, input_device, output_device)
        except Exception as e:
            print(f"Error saving device config: {e}")

    def on_test_audio(self, event):
        self.api.speak("Testing audio. You should hear a sound.")
        self.api.play_sound("startup")

    def on_theme_preview(self, event):
        theme_name = self.theme_choice.GetStringSelection()
        if theme_name:
            self.api.sounds.current_theme = theme_name
            self.api.play_sound("startup")
            self.api.speak(theme_name)

    def on_version_click(self, event):
        print("Version button clicked!")
        self.easter_egg_count += 1
        if self.easter_egg_count < 3:
            self.api.speak(f"{3 - self.easter_egg_count} more to unlock.")
        elif self.easter_egg_count == 3:
            self.api.speak("You found the secret! PyOS was made for YOU.")
            wx.MessageBox("You found the secret! PyOS was made for YOU.", "Easter Egg")
        else:
            self.api.speak("You're a PyOS master!")

    def on_speech_mode_change(self, event):
        self._apply_speech_mode_selection(announce=True)

    def _apply_speech_mode_selection(self, announce=True):
        sel = self.speech_choice.GetSelection()
        if sel < 0 or sel >= len(self.speech_modes): return
        speech_mode = self.speech_modes[sel][1]
        mode_ok = getattr(self.api.engine, "set_mode", lambda _m: False)(speech_mode)
        if not announce: return
        if speech_mode == "nvda" and not getattr(self.api.engine, "use_nvda", False):
            self.api.speak("NVDA is not active, so speech is using SAPI until NVDA is available.", interrupt=False)
        elif not mode_ok: pass

    def check_updates(self, event):
        self.api.speak("Checking for updates...")

    def run(self):
        self.frame = wx.Frame(None, title="Settings", size=(500, 600))
        notebook = wx.Notebook(self.frame)

        # --- General Tab ---
        gen_panel = wx.Panel(notebook)
        gen_sizer = wx.BoxSizer(wx.VERTICAL)
        notebook.AddPage(gen_panel, "General")

        title = wx.StaticText(gen_panel, label="System Settings")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        gen_sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        # Version info for Easter egg
        self.version_btn = wx.Button(gen_panel, label="Version: 2026.05.22 (Click for details)")
        self.version_btn.Bind(wx.EVT_BUTTON, self.on_version_click)
        gen_sizer.Add(self.version_btn, 0, wx.ALL | wx.CENTER, 5)

        theme_label = wx.StaticText(gen_panel, label="Sound Theme:")
        gen_sizer.Add(theme_label, 0, wx.ALL, 10)

        themes = self.api.sounds.get_available_themes()
        self.theme_choice = wx.Choice(gen_panel, choices=themes if themes else ["Modern"])
        current_theme = self.api.sounds.current_theme
        if current_theme in themes: self.theme_choice.SetSelection(themes.index(current_theme))
        else: self.theme_choice.SetSelection(0)
        self.theme_choice.Bind(wx.EVT_CHOICE, self.on_theme_preview)
        gen_sizer.Add(self.theme_choice, 0, wx.EXPAND | wx.ALL, 8)

        # Update button
        update_btn = wx.Button(gen_panel, label="Check for Updates")
        update_btn.Bind(wx.EVT_BUTTON, self.check_updates)
        gen_sizer.Add(update_btn, 0, wx.EXPAND | wx.ALL, 8)
        gen_panel.SetSizer(gen_sizer)

        # --- Speech Tab ---
        speech_panel = wx.Panel(notebook)
        speech_sizer = wx.BoxSizer(wx.VERTICAL)
        notebook.AddPage(speech_panel, "Speech")

        # Engine
        speech_label = wx.StaticText(speech_panel, label="Speech Engine:")
        speech_sizer.Add(speech_label, 0, wx.ALL, 10)
        self.speech_modes = [("Auto", "auto"), ("NVDA", "nvda"), ("SAPI", "sapi")]
        self.speech_choice = wx.Choice(speech_panel, choices=[m[0] for m in self.speech_modes])
        current_mode = getattr(self.api.engine, "get_mode", lambda: "auto")()
        idx = next((i for i, m in enumerate(self.speech_modes) if m[1] == current_mode), 0)
        self.speech_choice.SetSelection(idx)
        self.speech_choice.Bind(wx.EVT_CHOICE, self.on_speech_mode_change)
        speech_sizer.Add(self.speech_choice, 0, wx.EXPAND | wx.ALL, 8)

        # Speed
        speed_label = wx.StaticText(speech_panel, label="Voice Speed:")
        speech_sizer.Add(speed_label, 0, wx.ALL, 10)
        current_rate = getattr(self.api.engine, "get_rate", lambda: 200)()
        self.speed_slider = wx.Slider(speech_panel, value=current_rate, minValue=50, maxValue=400, style=wx.SL_HORIZONTAL)
        self.speed_slider.Bind(wx.EVT_SLIDER, self.on_speed_change)
        speech_sizer.Add(self.speed_slider, 0, wx.EXPAND | wx.ALL, 10)
        speech_panel.SetSizer(speech_sizer)

        # --- Audio Tab ---
        audio_panel = wx.Panel(notebook)
        audio_sizer = wx.BoxSizer(wx.VERTICAL)
        notebook.AddPage(audio_panel, "Audio")

        if HAS_SOUNDDEVICE:
            input_label = wx.StaticText(audio_panel, label="Input Device (Microphone):")
            audio_sizer.Add(input_label, 0, wx.ALL, 8)
            self.input_entries = self.get_input_devices()
            input_labels = [self._device_label(d) for d in self.input_entries] or ["Default"]
            self.input_choice = wx.Choice(audio_panel, choices=input_labels)
            audio_sizer.Add(self.input_choice, 0, wx.EXPAND | wx.ALL, 8)

            output_label = wx.StaticText(audio_panel, label="Output Device (Speaker):")
            audio_sizer.Add(output_label, 0, wx.ALL, 8)
            self.output_entries = self.get_output_devices()
            output_labels = [self._device_label(d) for d in self.output_entries] or ["Default"]
            self.output_choice = wx.Choice(audio_panel, choices=output_labels)
            audio_sizer.Add(self.output_choice, 0, wx.EXPAND | wx.ALL, 8)

            test_btn = wx.Button(audio_panel, label="Test Audio")
            test_btn.Bind(wx.EVT_BUTTON, self.on_test_audio)
            audio_sizer.Add(test_btn, 0, wx.EXPAND | wx.ALL, 8)
        audio_panel.SetSizer(audio_sizer)
        
        self.frame.Show()

    def on_speed_change(self, event):
        rate = self.speed_slider.GetValue()
        self.apply_speed(rate)

    def apply_speed(self, rate):
        if hasattr(self.api.engine, "set_rate"):
            self.api.engine.set_rate(rate)
            self.api.speak(f"Speed {rate}", interrupt=True)
            self.api.terminal_output(f"System: Voice speed set to {rate}.")

    def get_terminal_commands(self):
        return {
            "speed <50-400>": "Set the system voice speed.",
            "version": "Show system version (keep typing it!)."
        }

    def terminal_input(self, command):
        # Allow setting speed from terminal: 'speed 300'
        parts = command.split()
        if not parts: return
        action = parts[0].lower()

        if action == "speed" and len(parts) >= 2:
            try:
                rate = int(parts[1])
                if 50 <= rate <= 400:
                    self.apply_speed(rate)
                    # Update slider if GUI is open
                    if self.frame:
                        self.speed_slider.SetValue(rate)
                else:
                    self.api.terminal_output("Error: Speed must be between 50 and 400.")
            except ValueError:
                self.api.terminal_output("Error: Invalid speed value.")
        elif action == "version":
            self.easter_egg_count += 1
            if self.easter_egg_count < 3:
                self.api.terminal_output(f"PyOS Build 2026.05.22. {3 - self.easter_egg_count} more to unlock.")
            elif self.easter_egg_count == 3:
                self.api.terminal_output("You found the secret! PyOS was made for YOU.")
                self.api.speak("You found the secret. PyOS was made for you.")
            else:
                self.api.terminal_output("You're a PyOS master!")
        else:
            self.api.terminal_output("Settings commands: 'speed <value>', 'version'")
