import wx
import os
from api import BlindApp

class ThemeCreatorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Theme Creator"
        self.description = "Create your own sound theme."
        self.docs = "Theme Creator allows you to define custom tones or sound file paths for system events like startup, navigation, alerts, launch, close, alarms, and timers." 
        self.frame = None
        self.label = None
        self.theme_name_input = None
        self.mode_choice = None
        self.freq_input = None
        self.duration_input = None
        self.file_path_input = None
        self.browse_btn = None
        self.btn = None
        self.step = "theme_name"
        self.current_event_index = 0
        self.events = ["startup", "nav", "alert", "launch", "close", "alarm", "timer"]
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"

    def run(self):
        self.step = "theme_name"
        self.current_event_index = 0
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"

        self.frame = wx.Frame(None, title="Theme Creator", size=(520, 430))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        self.label = wx.StaticText(panel, label="Enter name for new theme:")
        self.label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.label, 0, wx.ALL | wx.CENTER, 10)

        self.theme_name_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.theme_name_input.SetToolTip("Enter the name for your custom sound theme.")
        self.theme_name_input.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.theme_name_input, 0, wx.EXPAND | wx.ALL, 10)

        self.mode_choice = wx.Choice(panel, choices=["Tones", "Audio File"])
        self.mode_choice.SetToolTip("Select whether to use generated tones or an external audio file.")
        self.mode_choice.SetSelection(0)
        self.mode_choice.Hide()
        sizer.Add(self.mode_choice, 0, wx.EXPAND | wx.ALL, 10)

        self.freq_label = wx.StaticText(panel, label="Frequencies (e.g. 440, 660, 0):")
        self.freq_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.freq_label.Hide()
        sizer.Add(self.freq_label, 0, wx.ALL, 8)
        self.freq_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.freq_input.Hide()
        sizer.Add(self.freq_input, 0, wx.EXPAND | wx.ALL, 8)

        self.dur_label = wx.StaticText(panel, label="Durations in milliseconds (e.g. 200, 300, 500):")
        self.dur_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.dur_label.Hide()
        sizer.Add(self.dur_label, 0, wx.ALL, 8)
        self.duration_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.duration_input.Hide()
        sizer.Add(self.duration_input, 0, wx.EXPAND | wx.ALL, 8)

        self.file_label = wx.StaticText(panel, label="Audio File Path:")
        self.file_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.file_label.Hide()
        sizer.Add(self.file_label, 0, wx.ALL, 8)
        file_row = wx.BoxSizer(wx.HORIZONTAL)
        self.file_path_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.file_path_input.Hide()
        file_row.Add(self.file_path_input, 1, wx.EXPAND | wx.RIGHT, 8)
        self.browse_btn = wx.Button(panel, label="Browse...")
        self.browse_btn.Hide()
        file_row.Add(self.browse_btn, 0)
        sizer.Add(file_row, 0, wx.EXPAND | wx.ALL, 8)

        self.btn = wx.Button(panel, label="Next")
        sizer.Add(self.btn, 0, wx.ALL | wx.CENTER, 10)
        panel.SetSizer(sizer)

        self.btn.Bind(wx.EVT_BUTTON, self.on_next)
        self.theme_name_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.freq_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.duration_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.file_path_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.on_browse_file)
        self.mode_choice.Bind(wx.EVT_CHOICE, self.on_mode_changed)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)

        self.frame.Show()
        self.api.speak("Theme Creator opened. Enter a name for your theme.")
        self.set_step_ui("theme_name")

    def on_key_press(self, event):
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.on_next()
            return
        event.Skip()

    def on_mode_changed(self, event):
        selected = self.mode_choice.GetStringSelection().lower()
        self.sound_choice_mode = "tones" if selected == "tones" else "file"
        if self.step == "event":
            self.update_event_inputs()

    def update_event_inputs(self):
        if self.sound_choice_mode == "tones":
            self.freq_input.Show()
            self.duration_input.Show()
            self.file_path_input.Hide()
            self.browse_btn.Hide()
            self.api.speak("Tone mode. Enter frequencies then durations.")
        else:
            self.freq_input.Hide()
            self.duration_input.Hide()
            self.file_path_input.Show()
            self.browse_btn.Show()
            self.api.speak("File mode. Type a path or browse.")
        self.frame.Layout()

    def set_step_ui(self, step):
        self.step = step
        self.theme_name_input.Hide()
        self.mode_choice.Hide()
        self.freq_input.Hide()
        self.duration_input.Hide()
        self.file_path_input.Hide()
        self.browse_btn.Hide()

        if step == "theme_name":
            self.label.SetLabel("Enter name for new theme:")
            self.theme_name_input.Show()
            self.theme_name_input.SetFocus()
            self.api.speak("Enter a name for your theme, then press Next.")
        elif step == "event":
            self.label.SetLabel(f"{self.current_event.capitalize()}: choose source and enter values.")
            self.mode_choice.Show()
            self.mode_choice.SetFocus()
            self.update_event_inputs()

        self.frame.Layout()

    def on_next(self, event=None):
        if self.step == "theme_name":
            val = self.theme_name_input.GetValue().strip()
            if not val:
                self.api.speak("Theme name is required.")
                self.theme_name_input.SetFocus()
                return
            self.theme_name_input.Clear()
            self.theme_name = val
            self.current_event = self.events[self.current_event_index]
            self.set_step_ui("event")
            return

        if self.step == "event":
            selected = self.mode_choice.GetStringSelection().lower() or "tones"
            self.sound_choice_mode = "tones" if selected == "tones" else "file"
            if self.sound_choice_mode == "tones":
                try:
                    tones = self.parse_tone_input(
                        self.freq_input.GetValue().strip(),
                        self.duration_input.GetValue().strip()
                    )
                    self.new_theme[self.current_event] = tones
                    self.freq_input.Clear()
                    self.duration_input.Clear()
                    self.api.speak(f"{self.current_event.capitalize()} tone set.")
                    self.advance_to_next_event()
                except ValueError as e:
                    self.api.speak(f"Invalid tone input: {e}")
                    self.freq_input.SetFocus()
                return
            path = self.file_path_input.GetValue().strip()
            if not path:
                self.api.speak("File path is required, or use Browse.")
                self.file_path_input.SetFocus()
                return
            if not os.path.exists(path):
                self.api.speak("File path not found. Please enter a valid audio file path.")
                self.file_path_input.SetFocus()
                return
            self.new_theme[self.current_event] = path
            self.file_path_input.Clear()
            self.api.speak(f"{self.current_event.capitalize()} sound set to file.")
            self.advance_to_next_event()

    def parse_int_list(self, raw_text, field_name):
        parts = [p.strip() for p in raw_text.split(",")]
        if not parts or any(p == "" for p in parts):
            raise ValueError(f"{field_name} must be comma-separated values")
        values = []
        for part in parts:
            try:
                values.append(int(part))
            except ValueError:
                raise ValueError(f"{field_name} must contain only whole numbers")
        return values

    def validate_tone_safety(self, freq, duration):
        if freq >= 8000 and duration > 120:
            raise ValueError("frequencies 8000 Hz or higher must be 120 ms or less")
        if freq >= 4000 and duration > 300:
            raise ValueError("frequencies 4000 Hz or higher must be 300 ms or less")

    def parse_tone_input(self, freq_text, duration_text):
        freqs = self.parse_int_list(freq_text, "Frequencies")
        durs = self.parse_int_list(duration_text, "Durations")
        if len(freqs) != len(durs):
            raise ValueError("frequencies and durations must have the same number of items")

        tones = []
        for freq, duration in zip(freqs, durs):
            if freq < 0:
                raise ValueError("frequency cannot be negative; use 0 for silence")
            if duration <= 0:
                raise ValueError("duration must be greater than zero")
            if freq > 0:
                self.validate_tone_safety(freq, duration)
            tones.append((freq, duration))
        return tones

    def on_browse_file(self, event):
        wildcard = "Audio files (*.wav;*.mp3;*.ogg;*.flac)|*.wav;*.mp3;*.ogg;*.flac|WAV files (*.wav)|*.wav|MP3 files (*.mp3)|*.mp3|OGG files (*.ogg)|*.ogg|FLAC files (*.flac)|*.flac"
        dlg = wx.FileDialog(self.frame, "Choose an audio file", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.file_path_input.SetValue(dlg.GetPath())
            self.api.speak("File selected.")
        dlg.Destroy()

    def advance_to_next_event(self):
        self.current_event_index += 1
        if self.current_event_index < len(self.events):
            self.current_event = self.events[self.current_event_index]
            self.set_step_ui("event")
        else:
            self.finalize_theme()

    def finalize_theme(self):
        # Set default tones for launch/close if they weren't configured interactively
        # These are hardcoded defaults, could be made configurable in a more robust app.
        if "launch" not in self.new_theme or not self.new_theme["launch"]:
             self.new_theme["launch"] = [(800, 100)]
        if "close" not in self.new_theme or not self.new_theme["close"]:
             self.new_theme["close"] = [(400, 100)]

        if self.theme_name and self.new_theme:
            # Add the new theme to the in-memory themes dictionary
            self.api.sounds.themes[self.theme_name] = self.new_theme
            
            # To make this theme persistent, we need to save it to user_themes.json.
            # Call the newly implemented save_custom_themes method.
            self.api.sounds.save_custom_themes() 

            # Apply the new theme immediately as the current theme
            self.api.sounds.save_theme_name(self.theme_name)
            self.api.speak(f"Theme {self.theme_name} created and applied!")
        else:
            self.api.speak("Theme creation failed. Please ensure all required inputs were provided.")
            
        self.on_close()

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
