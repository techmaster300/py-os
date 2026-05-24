import wx
import os
import threading
from api import BlindApp

class ThemeCreatorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Theme Creator"
        self.description = "Create your own sound theme."
        self.docs = "Theme Creator lets you define tones or sound files for each system event."
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
        self.events = ["startup", "nav", "launch", "close", "alert", "shutdown", "power_menu", "context_menu", "notify", "logon", "logoff", "error", "alarm", "timer", "info", "complete", "device_connect", "device_disconnect"]
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"

    def run(self, path=None):
        self.step = "theme_name"
        self.current_event_index = 0
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"

        self._create_frame("Theme Creator", (520, 430))
        panel = self.make_panel(self.frame, "Theme Creator Panel")
        sizer = self.vbox()

        self.label = self.make_static(panel, "Enter name for new theme:", "Theme Prompt", size=(-1, -1))
        self.label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(self.label, 0, wx.ALL | wx.CENTER, 10)

        self.theme_name_input = self.make_textctrl(panel, name="Theme Name", style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.theme_name_input, 0, wx.EXPAND | wx.ALL, 10)

        self.mode_choice = self.make_choice(panel, ["Tones", "Audio File"], "Sound Mode")
        self.mode_choice.SetSelection(0)
        self.mode_choice.Bind(wx.EVT_CHOICE, self.on_mode_changed)
        sizer.Add(self.mode_choice, 0, wx.EXPAND | wx.ALL, 10)

        self.freq_input = self.make_textctrl(panel, name="Frequencies", style=wx.TE_PROCESS_ENTER)
        self.freq_input.SetHint("Frequencies, e.g. 440, 660, 0")
        self.freq_input.Hide()
        sizer.Add(self.freq_input, 0, wx.EXPAND | wx.ALL, 8)

        self.duration_input = self.make_textctrl(panel, name="Durations", style=wx.TE_PROCESS_ENTER)
        self.duration_input.SetHint("Durations ms, e.g. 200, 300, 500")
        self.duration_input.Hide()
        sizer.Add(self.duration_input, 0, wx.EXPAND | wx.ALL, 8)

        file_row = self.hbox()
        self.file_path_input = self.make_textctrl(panel, name="File Path", style=wx.TE_PROCESS_ENTER)
        self.file_path_input.SetHint("Type file path or click Browse")
        self.file_path_input.Hide()
        file_row.Add(self.file_path_input, 1, wx.EXPAND | wx.RIGHT, 8)
        self.browse_btn = self.make_button(panel, "Browse...", self.on_browse_file, "Browse File")
        self.browse_btn.Hide()
        file_row.Add(self.browse_btn, 0)
        sizer.Add(file_row, 0, wx.EXPAND | wx.ALL, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.test_btn = self.make_button(panel, "Test", self.on_test_sound, "Test Sound")
        self.test_btn.Hide()
        btn_row.Add(self.test_btn, 0, wx.RIGHT, 10)
        self.btn = self.make_button(panel, "Next", self.on_next, "Next")
        btn_row.Add(self.btn, 0)
        sizer.Add(btn_row, 0, wx.ALL | wx.CENTER, 10)

        self.theme_name_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.freq_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.duration_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.file_path_input.Bind(wx.EVT_TEXT_ENTER, self.on_next)

        panel.SetSizer(sizer)
        self.set_step_ui("theme_name")
        self.api.speak("Theme Creator opened. Enter a name for your theme.")
        self._show_app(self.theme_name_input)

    def on_mode_changed(self, event):
        selected = self.mode_choice.GetStringSelection().lower()
        self.sound_choice_mode = "tones" if selected == "tones" else "file"
        if self.step == "event":
            self.update_event_inputs()

    def update_event_inputs(self):
        leave_focus = self.mode_choice.HasFocus()
        if self.sound_choice_mode == "tones":
            self.freq_input.Show()
            self.duration_input.Show()
            self.file_path_input.Hide()
            self.browse_btn.Hide()
            if not leave_focus:
                self.freq_input.SetFocus()
            self.api.speak("Tone mode. Enter frequencies then durations.")
        else:
            self.freq_input.Hide()
            self.duration_input.Hide()
            self.file_path_input.Show()
            self.browse_btn.Show()
            if not leave_focus:
                self.file_path_input.SetFocus()
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
        self.test_btn.Hide()

        if step == "theme_name":
            self.label.SetLabel("Enter name for new theme:")
            self.theme_name_input.Show()
            self.theme_name_input.SetFocus()
            self.api.speak("Enter a name for your theme, then press Next.")
        elif step == "event":
            self.label.SetLabel(f"{self.current_event.capitalize()}: choose source and enter values.")
            self.mode_choice.Show()
            self.test_btn.Show()
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
                self.api.speak("File path not found.")
                self.file_path_input.SetFocus()
                return
            self.new_theme[self.current_event] = path
            self.file_path_input.Clear()
            self.api.speak(f"{self.current_event.capitalize()} sound set to file.")
            self.advance_to_next_event()

    def on_test_sound(self, event=None):
        if self.step != "event":
            return
        selected = self.mode_choice.GetStringSelection().lower() or "tones"
        if selected == "tones":
            try:
                tones = self.parse_tone_input(
                    self.freq_input.GetValue().strip(),
                    self.duration_input.GetValue().strip()
                )
                self.api.sounds.preview(tones)
            except ValueError as e:
                self.api.speak(f"Cannot test: {e}")
        else:
            path = self.file_path_input.GetValue().strip()
            if path and os.path.exists(path):
                self.api.sounds.preview(path)
            else:
                self.api.speak("Set a valid file path first.")

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
        wildcard = "Audio files (*.wav;*.mp3;*.ogg;*.flac)|*.wav;*.mp3;*.ogg;*.flac"
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
        if "launch" not in self.new_theme or not self.new_theme["launch"]:
            self.new_theme["launch"] = [(800, 100)]
        if "close" not in self.new_theme or not self.new_theme["close"]:
            self.new_theme["close"] = [(400, 100)]
        if self.theme_name and self.new_theme:
            self.api.sounds.themes[self.theme_name] = self.new_theme
            self.api.sounds.save_custom_themes()
            self.api.sounds.save_theme_name(self.theme_name)
            self.api.speak(f"Theme {self.theme_name} created and applied!")
        else:
            self.api.speak("Theme creation failed.")
        self.on_close()

    def on_close(self, event=None):
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
