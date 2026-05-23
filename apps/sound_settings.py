import wx
import os
import threading
from api import BlindApp

class ThemeCreatorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Sound Theme Manager"
        self.description = "Create and manage custom sound themes."
        self.docs = "Create new sound themes or rename/delete existing custom themes."
        self.frame = None
        self.mode = "choose"
        self.label = None
        self.theme_name_input = None
        self.mode_choice = None
        self.freq_input = None
        self.duration_input = None
        self.file_path_input = None
        self.browse_btn = None
        self.btn = None
        self.preview_btn = None
        self.step = "theme_name"
        self.events = ["startup", "nav", "alert", "launch", "close", "alarm", "timer"]
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"
        self.manage_list = None

    def run(self):
        self._create_frame("Sound Theme Manager", (520, 430))
        panel = self.make_panel(self.frame)
        sizer = self.vbox()

        self.label = wx.StaticText(panel, label="Choose an option:")
        self.label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.label.SetName("Heading")
        sizer.Add(self.label, 0, wx.ALL | wx.CENTER, 15)

        create_btn = self.make_button(panel, "Create New Theme", lambda evt: self.start_create())
        sizer.Add(create_btn, 0, wx.EXPAND | wx.ALL, 10)

        manage_btn = self.make_button(panel, "Manage Custom Themes", lambda evt: self.start_manage())
        sizer.Add(manage_btn, 0, wx.EXPAND | wx.ALL, 10)

        self.theme_name_input = self.make_textctrl(panel, name="Theme Name", style=wx.TE_PROCESS_ENTER)
        self.theme_name_input.Hide()

        self.mode_choice = self.make_choice(panel, ["Tones", "Audio File"], "Sound Mode")
        self.mode_choice.SetSelection(0)
        self.mode_choice.Bind(wx.EVT_CHOICE, self.on_mode_change)

        self.freq_label = self.make_static(panel, "Frequencies (e.g. 440, 660, 0):", "Frequencies Label")
        self.freq_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.freq_input = self.make_textctrl(panel, name="Frequencies Input", style=wx.TE_PROCESS_ENTER)
        self.dur_label = self.make_static(panel, "Durations in ms (e.g. 200, 300, 500):", "Durations Label")
        self.dur_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.duration_input = self.make_textctrl(panel, name="Durations Input", style=wx.TE_PROCESS_ENTER)
        self.file_label = self.make_static(panel, "Audio File Path:", "File Path Label")
        self.file_label.SetForegroundColour(wx.Colour(255, 255, 255))
        file_row = self.hbox()
        self.file_path_input = self.make_textctrl(panel, name="File Path", style=wx.TE_PROCESS_ENTER)
        self.browse_btn = self.make_button(panel, "Browse...", self.on_browse_file, "Browse File")
        file_row.Add(self.file_path_input, 1, wx.EXPAND | wx.RIGHT, 8)
        file_row.Add(self.browse_btn, 0)
        self.file_path_input.Hide()
        self.browse_btn.Hide()

        self.manage_list = self.make_listbox(panel, name="Custom Themes List")
        self.manage_list.Bind(wx.EVT_LISTBOX, self.on_manage_select)

        btn_row = self.hbox()
        self.btn = self.make_button(panel, "Next", self.on_next, "Next")
        btn_row.Add(self.btn, 1, wx.ALL, 5)
        self.preview_btn = self.make_button(panel, "Preview", self.on_preview, "Preview Sound")
        btn_row.Add(self.preview_btn, 1, wx.ALL, 5)
        sizer.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.manage_btn_row = self.hbox()
        self.rename_btn = self.make_button(panel, "Rename", self.on_rename_theme, "Rename Theme")
        self.manage_btn_row.Add(self.rename_btn, 1, wx.ALL, 3)
        self.delete_btn = self.make_button(panel, "Delete", self.on_delete_theme, "Delete Theme")
        self.manage_btn_row.Add(self.delete_btn, 1, wx.ALL, 3)
        self.apply_btn = self.make_button(panel, "Apply", self.on_apply_theme, "Apply Theme")
        self.manage_btn_row.Add(self.apply_btn, 1, wx.ALL, 3)

        self.status_label = self.make_static(panel, "", "Status")
        self.status_label.SetForegroundColour(wx.Colour(200, 200, 200))

        panel.SetSizer(sizer)
        self.api.speak("Sound Theme Manager opened. Create a new theme or manage existing ones.")
        self._show_app(create_btn)

    def on_mode_change(self, event):
        self.sound_choice_mode = "tones" if self.mode_choice.GetStringSelection().lower() == "tones" else "file"
        self._update_event_inputs()

    def start_create(self):
        self._clear_ui()
        self.step = "theme_name"
        self.new_theme = {}
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "tones"
        self.label.SetLabel("Enter name for new theme:")
        self.theme_name_input.Show()
        self.theme_name_input.SetFocus()
        self.btn.Show()
        self.btn.SetLabel("Next")
        self.api.speak("Enter a name for your theme.")
        self.frame.Layout()
        for widget in [self.freq_label, self.freq_input, self.dur_label, self.duration_input,
                       self.file_label, self.file_path_input, self.browse_btn, self.mode_choice,
                       self.preview_btn, self.manage_list, self.manage_btn_row, self.status_label]:
            widget.Hide()
        self.theme_name_input.Bind(wx.EVT_TEXT_ENTER, self.on_create_next)

    def start_manage(self):
        self._clear_ui()
        custom_themes = [t for t in self.api.sounds.themes if t not in self.api.sounds.default_themes]
        if not custom_themes:
            self.alert("No custom themes to manage.")
            self.label.SetLabel("No custom themes found. Create one first.")
            self.label.Show()
            return

        self.manage_list.Set(custom_themes)
        self.label.SetLabel("Select a custom theme:")
        self.manage_list.Show()
        self.manage_btn_row.Show()
        self.status_label.Show()
        self.api.speak(f"{len(custom_themes)} custom themes. Select one to manage.")
        self.frame.Layout()

    def _clear_ui(self):
        for w in [self.theme_name_input, self.mode_choice, self.freq_label, self.freq_input,
                  self.dur_label, self.duration_input, self.file_label, self.file_path_input,
                  self.browse_btn, self.btn, self.preview_btn, self.manage_list, self.manage_btn_row,
                  self.status_label]:
            w.Hide()

    def on_manage_select(self, event):
        sel = self.manage_list.GetSelection()
        if sel != wx.NOT_FOUND:
            name = self.manage_list.GetString(sel)
            current = "(current)" if name == self.api.sounds.current_theme else ""
            self.status_label.SetLabel(f"{name} {current}")
            self.api.speak(f"{name} {current}")

    def on_rename_theme(self, event):
        sel = self.manage_list.GetSelection()
        if sel == wx.NOT_FOUND:
            self.api.speak("Select a theme first.")
            return
        old_name = self.manage_list.GetString(sel)
        if old_name in self.api.sounds.default_themes:
            self.alert("Cannot rename default themes.")
            return
        new_name = self.prompt("New name:", default=old_name, title="Rename Theme")
        if new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            self.api.sounds.themes[new_name] = self.api.sounds.themes.pop(old_name)
            self.api.sounds.save_custom_themes()
            if self.api.sounds.current_theme == old_name:
                self.api.sounds.save_theme_name(new_name)
            self.api.speak(f"Renamed to {new_name}.")
            self.start_manage()

    def on_delete_theme(self, event):
        sel = self.manage_list.GetSelection()
        if sel == wx.NOT_FOUND:
            self.api.speak("Select a theme first.")
            return
        name = self.manage_list.GetString(sel)
        if name in self.api.sounds.default_themes:
            self.alert("Cannot delete default themes.")
            return
        if self.confirm(f"Delete theme '{name}'?", "Confirm"):
            self.api.sounds.themes.pop(name, None)
            self.api.sounds.save_custom_themes()
            if self.api.sounds.current_theme == name:
                self.api.sounds.save_theme_name("Modern")
            self.api.speak(f"Deleted {name}.")
            self.start_manage()

    def on_apply_theme(self, event):
        sel = self.manage_list.GetSelection()
        if sel == wx.NOT_FOUND:
            self.api.speak("Select a theme first.")
            return
        name = self.manage_list.GetString(sel)
        self.api.sounds.save_theme_name(name)
        self.api.speak(f"Theme {name} applied.")
        self.status_label.SetLabel(f"{name} (current)")

    def on_create_next(self, event=None):
        val = self.theme_name_input.GetValue().strip()
        if not val:
            self.api.speak("Theme name is required.")
            return
        self.theme_name_input.Clear()
        self.theme_name = val
        self.theme_name_input.Hide()
        self._advance()

    def _show_event_ui(self):
        self.step = "event"
        self.mode = "event"
        self.label.SetLabel(f"{self.current_event.capitalize()}: choose source and enter values.")
        self.mode_choice.Show()
        self.mode_choice.SetFocus()
        self.preview_btn.Show()
        self.btn.Show()
        self.btn.SetLabel("Next")
        self._update_event_inputs()
        self.frame.Layout()

    def _update_event_inputs(self):
        if self.sound_choice_mode == "tones":
            self.freq_label.Show()
            self.freq_input.Show()
            self.dur_label.Show()
            self.duration_input.Show()
            self.file_label.Hide()
            self.file_path_input.Hide()
            self.browse_btn.Hide()
        else:
            self.freq_label.Hide()
            self.freq_input.Hide()
            self.dur_label.Hide()
            self.duration_input.Hide()
            self.file_label.Show()
            self.file_path_input.Show()
            self.browse_btn.Show()
        self.frame.Layout()

    def on_preview(self, event):
        selected = self.mode_choice.GetStringSelection().lower() or "tones"
        if selected == "tones":
            try:
                tones = self.parse_tone_input(
                    self.freq_input.GetValue().strip(),
                    self.duration_input.GetValue().strip()
                )
                self.api.sounds._play_notes(tones)
            except ValueError as e:
                self.api.speak(f"Cannot preview: {e}")
        else:
            path = self.file_path_input.GetValue().strip()
            if os.path.exists(path):
                threading.Thread(target=self.api.sounds._play_file, args=(path,), daemon=True).start()
            else:
                self.api.speak("File not found for preview.")

    def on_next(self, event=None):
        if self.mode == "event":
            self.on_event_next()
        elif self.mode == "choose":
            pass

    def on_event_next(self):
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
                self._advance()
            except ValueError as e:
                self.api.speak(f"Invalid: {e}")
                self.freq_input.SetFocus()
        else:
            path = self.file_path_input.GetValue().strip()
            if not path:
                self.api.speak("File path required.")
                return
            if not os.path.exists(path):
                self.api.speak("File not found.")
                return
            self.new_theme[self.current_event] = path
            self.file_path_input.Clear()
            self.api.speak(f"{self.current_event.capitalize()} sound set.")
            self._advance()

    def _advance(self):
        remaining = [e for e in self.events if e not in self.new_theme]
        if not remaining:
            self._finalize()
            return
        choice = self.choice("Select event to configure:", remaining, title="Event Selection")
        if choice is None:
            self._finalize()
            return
        self.current_event = choice
        self._show_event_ui()

    def _finalize(self):
        if "launch" not in self.new_theme:
            self.new_theme["launch"] = [(800, 100)]
        if "close" not in self.new_theme:
            self.new_theme["close"] = [(400, 100)]

        if self.theme_name and self.new_theme:
            self.api.sounds.themes[self.theme_name] = self.new_theme
            self.api.sounds.save_custom_themes()
            self.api.sounds.save_theme_name(self.theme_name)
            self.api.speak(f"Theme {self.theme_name} created and applied!")
        else:
            self.api.speak("Theme creation failed.")

        self.on_close()

    def parse_int_list(self, raw_text, field_name):
        parts = [p.strip() for p in raw_text.split(",")]
        if not parts or any(p == "" for p in parts):
            raise ValueError(f"{field_name} must be comma-separated")
        values = []
        for part in parts:
            try:
                values.append(int(part))
            except ValueError:
                raise ValueError(f"{field_name} must be whole numbers")
        return values

    def validate_tone_safety(self, freq, duration):
        if freq >= 8000 and duration > 120:
            raise ValueError("freq >= 8000 Hz must be <= 120 ms")
        if freq >= 4000 and duration > 300:
            raise ValueError("freq >= 4000 Hz must be <= 300 ms")

    def parse_tone_input(self, freq_text, duration_text):
        freqs = self.parse_int_list(freq_text, "Frequencies")
        durs = self.parse_int_list(duration_text, "Durations")
        if len(freqs) != len(durs):
            raise ValueError("frequencies and durations must match in count")
        tones = []
        for freq, duration in zip(freqs, durs):
            if freq < 0:
                raise ValueError("frequency cannot be negative")
            if duration <= 0:
                raise ValueError("duration must be > 0")
            if freq > 0:
                self.validate_tone_safety(freq, duration)
            tones.append((freq, duration))
        return tones

    def on_browse_file(self, event):
        wildcard = "Audio files (*.wav;*.mp3;*.ogg;*.flac)|*.wav;*.mp3;*.ogg;*.flac"
        dlg = wx.FileDialog(self.frame, "Choose audio file", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.file_path_input.SetValue(dlg.GetPath())
            self.api.speak("File selected.")
        dlg.Destroy()

    def on_close(self, event=None):
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
