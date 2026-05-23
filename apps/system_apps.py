import wx
import os
import datetime
import subprocess
import speech
from api import BlindApp
import audio_devices
import config_manager
import translation
import lockscreen

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
        self.config = config_manager.load_config(self.api.data_dir)
        self.notebook = None
        self.dev_panel = None

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

    def on_language_change(self, event):
        codes = list(translation.available_languages().keys())
        sel = self.lang_choice.GetSelection()
        if 0 <= sel < len(codes):
            lang_code = codes[sel]
            self.config["language"] = lang_code
            config_manager.save_config(self.api.data_dir, self.config)
            translation.set_language(lang_code)
            self.api.speak(f"Language changed to {lang_code.upper()}")

    def on_theme_preview(self, event):
        theme_name = self.theme_choice.GetStringSelection()
        if theme_name:
            self.api.sounds.current_theme = theme_name
            self.api.play_sound("startup")
            self.api.speak(theme_name)

    def on_version_click(self, event):
        if self.config.get("developer_mode", False):
            self.api.speak("You are already a developer.")
            return
        config = lockscreen.load_config(self.api.data_dir)
        if config.get("hash"):
            self._show_dev_unlock_dialog(config)
        else:
            self._easter_egg_click()

    def add_dev_tab(self):
        if not self.notebook or self.dev_panel:
            return
        self.dev_panel = wx.Panel(self.notebook)
        dev_sizer = wx.BoxSizer(wx.VERTICAL)
        
        disable_btn = wx.Button(self.dev_panel, label="Disable Developer Options")
        disable_btn.Bind(wx.EVT_BUTTON, self.on_disable_dev_mode)
        dev_sizer.Add(disable_btn, 0, wx.ALL | wx.CENTER, 20)
        
        self.dev_panel.SetSizer(dev_sizer)
        self.notebook.AddPage(self.dev_panel, "Developer")
        self.api.speak("Developer tab added.")

    def on_disable_dev_mode(self, event):
        self.config["developer_mode"] = False
        config_manager.save_config(self.api.data_dir, self.config)
        self.easter_egg_count = 0
        self.api.speak("Developer mode disabled.")
        if self.dev_panel:
            # Find the page index by iterating or finding the panel
            for i in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(i) == self.dev_panel:
                    self.notebook.DeletePage(i)
                    break
            self.dev_panel.Destroy()
            self.dev_panel = None
            self.notebook.SetSelection(0)
            self.notebook.Refresh()

    def _activate_developer_mode(self):
        self.config["developer_mode"] = True
        config_manager.save_config(self.api.data_dir, self.config)
        self.api.speak("You are now a developer!")
        self.add_dev_tab()
        self.alert("You are now a developer!", "Developer Options")

    def _easter_egg_click(self):
        self.easter_egg_count += 1
        taps_left = 7 - self.easter_egg_count
        if taps_left > 0:
            self.api.speak(f"{taps_left} steps away from being a developer.")
        else:
            self._activate_developer_mode()

    def _show_dev_unlock_dialog(self, config):
        dlg = wx.Dialog(self.frame, title="Developer Unlock", size=(350, 420))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Enter your lock code")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        status = wx.StaticText(panel, label="")
        status.SetForegroundColour(wx.Colour(255, 80, 80))
        sizer.Add(status, 0, wx.ALL | wx.CENTER, 5)

        pin_buffer = [""]

        if config.get("lock_type") == "pin":
            display = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_CENTER, size=(150, 40))
            display.SetBackgroundColour(wx.Colour(30, 30, 30))
            display.SetForegroundColour(wx.Colour(255, 255, 255))
            display.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            sizer.Add(display, 0, wx.ALL | wx.CENTER, 10)

            def on_digit(d):
                pin_buffer[0] += d
                display.SetValue("*" * len(pin_buffer[0]))
                status.SetLabel("")

            def on_backspace():
                if pin_buffer[0]:
                    pin_buffer[0] = pin_buffer[0][:-1]
                    display.SetValue("*" * len(pin_buffer[0]))

            grid = wx.GridSizer(4, 3, 5, 5)
            keys = [
                ("1", "1"), ("2", "2"), ("3", "3"),
                ("4", "4"), ("5", "5"), ("6", "6"),
                ("7", "7"), ("8", "8"), ("9", "9"),
                ("", ""), ("0", "0"), ("⌫", "bs"),
            ]
            for label, action in keys:
                btn = wx.Button(panel, label=label, size=(70, 50))
                btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                if action == "bs":
                    btn.Bind(wx.EVT_BUTTON, lambda evt: on_backspace())
                elif action:
                    btn.Bind(wx.EVT_BUTTON, lambda evt, d=action: on_digit(d))
                grid.Add(btn, 0, wx.EXPAND)
            sizer.Add(grid, 0, wx.ALL | wx.CENTER, 10)
        else:
            pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, size=(200, 30))
            pwd_input.SetBackgroundColour(wx.Colour(30, 30, 30))
            pwd_input.SetForegroundColour(wx.Colour(255, 255, 255))
            sizer.Add(pwd_input, 0, wx.ALL | wx.CENTER, 10)

        def on_submit(evt):
            if config.get("lock_type") == "pin":
                value = pin_buffer[0]
            else:
                value = pwd_input.GetValue()
            if lockscreen.check(value, config):
                dlg.Close()
                self._activate_developer_mode()
            else:
                status.SetLabel("Incorrect. Try again.")
                pin_buffer[0] = ""
                if config.get("lock_type") == "pin":
                    display.SetValue("")
                else:
                    pwd_input.SetValue("")

        unlock_btn = wx.Button(panel, label="Unlock")
        unlock_btn.Bind(wx.EVT_BUTTON, on_submit)
        sizer.Add(unlock_btn, 0, wx.ALL | wx.CENTER, 10)

        cancel_btn = wx.Button(panel, label="Cancel")
        cancel_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(cancel_btn, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _update_lock_status_display(self, config=None):
        if not hasattr(self, 'lock_status_display'):
            return
        if config is None:
            config = lockscreen.load_config(self.api.data_dir)
        if config.get("enabled"):
            t = "PIN" if config.get("lock_type") == "pin" else "Password"
            self.lock_status_display.SetLabel(f"Lock: Enabled ({t})")
        else:
            self.lock_status_display.SetLabel("Lock: Disabled")

    def on_apply_appearance(self, event):
        c = {}
        c["desktop_bg"] = self.app_desk_bg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["desktop_button_bg"] = self.app_desk_btn_bg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["desktop_button_fg"] = self.app_desk_btn_fg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["desktop_header"] = self.app_desk_header.GetValue()
        c["desktop_header_color"] = self.app_desk_header_color.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["desktop_header_font_size"] = self.app_desk_header_fs.GetValue()
        c["desktop_button_font_size"] = self.app_desk_font_size.GetValue()
        c["desktop_button_spacing"] = self.app_desk_spacing.GetValue()
        c["desktop_greeting"] = self.app_desk_greeting.GetValue()
        c["desktop_width"] = self.app_desk_width.GetValue()
        c["desktop_height"] = self.app_desk_height.GetValue()
        c["lockscreen_bg"] = self.app_lock_bg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_title_color"] = self.app_lock_title.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_title_text"] = self.app_lock_title_text.GetValue()
        c["lockscreen_title_font_size"] = self.app_lock_title_fs.GetValue()
        c["lockscreen_mode_color"] = self.app_lock_mode.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_status_color"] = self.app_lock_status.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_input_bg"] = self.app_lock_input_bg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_input_fg"] = self.app_lock_input_fg.GetColour().GetAsString(wx.C2S_HTML_SYNTAX)
        c["lockscreen_display_font_size"] = self.app_lock_disp_fs.GetValue()
        c["lockscreen_input_font_size"] = self.app_lock_input_fs.GetValue()
        c["lockscreen_pin_font_size"] = self.app_lock_pin_fs.GetValue()
        c["lockscreen_mask_char"] = self.app_lock_mask.GetValue()
        c["lockscreen_width"] = self.app_lock_width.GetValue()
        c["lockscreen_height"] = self.app_lock_height.GetValue()
        config_manager.save_appearance_config(self.api.data_dir, c)
        self.api.speak("Appearance settings saved. Restart the desktop to see changes.")
        self.alert("Appearance settings saved. Restart the desktop to see changes.", "Appearance")

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
        self.api.speak("Starting system update.")
        
        # Execute update process asynchronously
        wx.CallAfter(self._execute_update)

    def _execute_update(self):
        try:
            # 1. Pull from git
            pull_result = subprocess.run(["git", "pull"], capture_output=True, text=True)
            if pull_result.returncode != 0:
                self.api.speak("Update failed.")
                return

            # 2. Update dependencies
            pip_result = subprocess.run(["pip", "install", "-r", "requirements.txt"], capture_output=True, text=True)
            
            if pip_result.returncode == 0:
                self.api.speak("System updated successfully.")
            else:
                self.api.speak("Dependencies failed to update.")
        
        except Exception:
            self.api.speak("An error occurred during update.")

    def run(self):
        self.frame = wx.Frame(None, title="Settings", size=(500, 600))
        self.notebook = wx.Notebook(self.frame)

        # --- General Tab ---
        gen_panel = wx.Panel(self.notebook)
        gen_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.AddPage(gen_panel, "General")

        title = wx.StaticText(gen_panel, label="System Settings")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        gen_sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        # Version info for Easter egg
        self.version_btn = wx.Button(gen_panel, label="Version: 2026.05.22 (Click for details)")
        self.version_btn.Bind(wx.EVT_BUTTON, self.on_version_click)
        gen_sizer.Add(self.version_btn, 0, wx.ALL | wx.CENTER, 5)

        lang_label = wx.StaticText(gen_panel, label="Language:")
        lang_label.SetName("Language Label")
        gen_sizer.Add(lang_label, 0, wx.ALL, 10)

        langs = translation.available_languages()
        lang_codes = list(langs.keys())
        lang_names = list(langs.values())
        self.lang_choice = wx.Choice(gen_panel, choices=lang_names)
        self.lang_choice.SetName("Language Selector")
        current_lang = self.config.get("language", "en")
        if current_lang in lang_codes:
            self.lang_choice.SetSelection(lang_codes.index(current_lang))
        else:
            self.lang_choice.SetSelection(0)
        self.lang_choice.Bind(wx.EVT_CHOICE, self.on_language_change)
        gen_sizer.Add(self.lang_choice, 0, wx.EXPAND | wx.ALL, 8)

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
        speech_panel = wx.Panel(self.notebook)
        speech_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.AddPage(speech_panel, "Speech")

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
        audio_panel = wx.Panel(self.notebook)
        audio_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.AddPage(audio_panel, "Audio")

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

        # --- Security Tab ---
        sec_panel = wx.Panel(self.notebook)
        sec_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.AddPage(sec_panel, "Security")

        sec_title = wx.StaticText(sec_panel, label="Lock Screen Settings")
        sec_title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sec_sizer.Add(sec_title, 0, wx.ALL | wx.CENTER, 15)

        lock_config = lockscreen.load_config(self.api.data_dir)

        self.lock_status_display = wx.StaticText(sec_panel, label="")
        sec_sizer.Add(self.lock_status_display, 0, wx.ALL | wx.CENTER, 5)
        self._update_lock_status_display(lock_config)

        self.lock_enabled = wx.CheckBox(sec_panel, label="Enable lock screen on startup")
        self.lock_enabled.SetValue(lock_config.get("enabled", False))
        sec_sizer.Add(self.lock_enabled, 0, wx.ALL, 10)

        type_label = wx.StaticText(sec_panel, label="Lock type:")
        sec_sizer.Add(type_label, 0, wx.LEFT | wx.RIGHT, 10)
        self.lock_type = wx.Choice(sec_panel, choices=["PIN", "Password"])
        self.lock_type.SetSelection(0 if lock_config.get("lock_type") == "pin" else 1)
        sec_sizer.Add(self.lock_type, 0, wx.EXPAND | wx.ALL, 10)

        code_label = wx.StaticText(sec_panel, label="Set new PIN or password:")
        sec_sizer.Add(code_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lock_input = wx.TextCtrl(sec_panel)
        sec_sizer.Add(self.lock_input, 0, wx.EXPAND | wx.ALL, 10)

        confirm_label = wx.StaticText(sec_panel, label="Confirm:")
        sec_sizer.Add(confirm_label, 0, wx.LEFT | wx.RIGHT, 10)
        self.lock_confirm = wx.TextCtrl(sec_panel)
        sec_sizer.Add(self.lock_confirm, 0, wx.EXPAND | wx.ALL, 10)

        save_lock_btn = wx.Button(sec_panel, label="Save Lock Settings")
        save_lock_btn.Bind(wx.EVT_BUTTON, self.on_save_lock)
        sec_sizer.Add(save_lock_btn, 0, wx.ALL | wx.CENTER, 10)

        auto_label = wx.StaticText(sec_panel, label="Auto-lock after:")
        sec_sizer.Add(auto_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.auto_lock_choice = wx.Choice(sec_panel, choices=["Never", "1 min", "5 min", "15 min", "30 min"])
        auto_val = lock_config.get("auto_lock_minutes", 0)
        auto_map = {0: 0, 1: 1, 5: 2, 15: 3, 30: 4}
        self.auto_lock_choice.SetSelection(auto_map.get(auto_val, 0))
        sec_sizer.Add(self.auto_lock_choice, 0, wx.EXPAND | wx.ALL, 10)

        self.lock_status = wx.StaticText(sec_panel, label="")
        sec_sizer.Add(self.lock_status, 0, wx.ALL | wx.CENTER, 5)

        clear_lock_btn = wx.Button(sec_panel, label="Disable & Clear Lock Code")
        clear_lock_btn.Bind(wx.EVT_BUTTON, self.on_clear_lock)
        sec_sizer.Add(clear_lock_btn, 0, wx.ALL | wx.CENTER, 5)

        sec_panel.SetSizer(sec_sizer)

        # --- Appearance Tab ---
        appearance_panel = wx.Panel(self.notebook)
        appearance_sizer = wx.BoxSizer(wx.VERTICAL)
        self.notebook.AddPage(appearance_panel, "Appearance")

        app_scroll = wx.ScrolledWindow(appearance_panel, style=wx.VSCROLL)
        app_scroll.SetScrollRate(0, 20)
        app_scroll.SetBackgroundColour(wx.Colour(0, 0, 0))
        app_scroll_sizer = wx.BoxSizer(wx.VERTICAL)

        app_config = config_manager.load_appearance_config(self.api.data_dir)

        def add_color_row(parent, sizer, label, config_key, default_color):
            row = wx.BoxSizer(wx.HORIZONTAL)
            txt = wx.StaticText(parent, label=label, size=(180, -1))
            txt.SetForegroundColour(wx.Colour(255, 255, 255))
            row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            ctrl = wx.ColourPickerCtrl(parent, colour=wx.Colour(app_config.get(config_key, default_color)))
            ctrl.SetName(label)
            row.Add(ctrl, 0, wx.ALL, 5)
            sizer.Add(row, 0, wx.EXPAND)
            return ctrl

        # Desktop section
        desk_label = wx.StaticText(app_scroll, label="Desktop")
        desk_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        desk_label.SetForegroundColour(wx.Colour(255, 255, 255))
        app_scroll_sizer.Add(desk_label, 0, wx.ALL | wx.CENTER, 10)

        self.app_desk_bg = add_color_row(app_scroll, app_scroll_sizer, "Background:", "desktop_bg", "#000000")
        self.app_desk_btn_bg = add_color_row(app_scroll, app_scroll_sizer, "Button background:", "desktop_button_bg", "#282828")
        self.app_desk_btn_fg = add_color_row(app_scroll, app_scroll_sizer, "Button text:", "desktop_button_fg", "#FFFFFF")

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Header text:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_header = wx.TextCtrl(app_scroll, value=app_config.get("desktop_header", "PyOS Desktop"), size=(200, -1))
        self.app_desk_header.SetName("Header text")
        self.app_desk_header.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_desk_header.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_desk_header, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        self.app_desk_header_color = add_color_row(app_scroll, app_scroll_sizer, "Header color:", "desktop_header_color", "#FFFFFF")

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Header font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_header_fs = wx.SpinCtrl(app_scroll, value=str(app_config.get("desktop_header_font_size", 18)), min=12, max=36, size=(80, -1))
        self.app_desk_header_fs.SetName("Header font size")
        row.Add(self.app_desk_header_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Button spacing:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_spacing = wx.SpinCtrl(app_scroll, value=str(app_config.get("desktop_button_spacing", 5)), min=0, max=30, size=(80, -1))
        self.app_desk_spacing.SetName("Button spacing")
        row.Add(self.app_desk_spacing, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Greeting text:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_greeting = wx.TextCtrl(app_scroll, value=app_config.get("desktop_greeting", "Welcome to PyOS. Use Tab to navigate through apps, and press Enter to launch."), size=(250, -1))
        self.app_desk_greeting.SetName("Greeting text")
        self.app_desk_greeting.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_desk_greeting.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_desk_greeting, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Button font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_font_size = wx.SpinCtrl(app_scroll, value=str(app_config.get("desktop_button_font_size", 16)), min=10, max=32, size=(80, -1))
        self.app_desk_font_size.SetName("Button font size")
        row.Add(self.app_desk_font_size, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Window size (W x H):", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        width_label = wx.StaticText(app_scroll, label="W:")
        width_label.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(width_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_desk_width = wx.SpinCtrl(app_scroll, value=str(app_config.get("desktop_width", 800)), min=600, max=1600, size=(80, -1))
        self.app_desk_width.SetName("Desktop width")
        row.Add(self.app_desk_width, 0, wx.ALL, 5)
        height_label = wx.StaticText(app_scroll, label="H:")
        height_label.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(height_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_desk_height = wx.SpinCtrl(app_scroll, value=str(app_config.get("desktop_height", 600)), min=400, max=1200, size=(80, -1))
        self.app_desk_height.SetName("Desktop height")
        row.Add(self.app_desk_height, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        # Lock screen section
        sep2 = wx.StaticLine(app_scroll, style=wx.LI_HORIZONTAL)
        app_scroll_sizer.Add(sep2, 0, wx.EXPAND | wx.ALL, 10)

        lock_label = wx.StaticText(app_scroll, label="Lock Screen")
        lock_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        lock_label.SetForegroundColour(wx.Colour(255, 255, 255))
        app_scroll_sizer.Add(lock_label, 0, wx.ALL | wx.CENTER, 10)

        self.app_lock_bg = add_color_row(app_scroll, app_scroll_sizer, "Background:", "lockscreen_bg", "#000000")
        self.app_lock_title = add_color_row(app_scroll, app_scroll_sizer, "Title color:", "lockscreen_title_color", "#FFFFFF")
        self.app_lock_mode = add_color_row(app_scroll, app_scroll_sizer, "Mode label:", "lockscreen_mode_color", "#B4B4B4")
        self.app_lock_status = add_color_row(app_scroll, app_scroll_sizer, "Status color:", "lockscreen_status_color", "#FF5050")
        self.app_lock_input_bg = add_color_row(app_scroll, app_scroll_sizer, "Input background:", "lockscreen_input_bg", "#1E1E1E")
        self.app_lock_input_fg = add_color_row(app_scroll, app_scroll_sizer, "Input text:", "lockscreen_input_fg", "#FFFFFF")

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Title text:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_title_text = wx.TextCtrl(app_scroll, value=app_config.get("lockscreen_title_text", "Lock Screen"), size=(200, -1))
        self.app_lock_title_text.SetName("Lock screen title text")
        self.app_lock_title_text.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_lock_title_text.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_lock_title_text, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Title font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_title_fs = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_title_font_size", 18)), min=12, max=36, size=(80, -1))
        self.app_lock_title_fs.SetName("Lock screen title font size")
        row.Add(self.app_lock_title_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Display font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_disp_fs = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_display_font_size", 20)), min=12, max=36, size=(80, -1))
        self.app_lock_disp_fs.SetName("Lock screen display font size")
        row.Add(self.app_lock_disp_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Input font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_input_fs = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_input_font_size", 14)), min=10, max=24, size=(80, -1))
        self.app_lock_input_fs.SetName("Lock screen input font size")
        row.Add(self.app_lock_input_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="PIN pad font size:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_pin_fs = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_pin_font_size", 14)), min=10, max=24, size=(80, -1))
        self.app_lock_pin_fs.SetName("PIN pad font size")
        row.Add(self.app_lock_pin_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Mask character:", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_mask = wx.TextCtrl(app_scroll, value=app_config.get("lockscreen_mask_char", "*"), size=(40, -1))
        self.app_lock_mask.SetMaxLength(1)
        self.app_lock_mask.SetName("Mask character")
        self.app_lock_mask.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_lock_mask.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_lock_mask, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        txt = wx.StaticText(app_scroll, label="Dialog size (W x H):", size=(180, -1))
        txt.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(txt, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        wl = wx.StaticText(app_scroll, label="W:")
        wl.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(wl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_lock_width = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_width", 350)), min=250, max=800, size=(80, -1))
        self.app_lock_width.SetName("Lock screen width")
        row.Add(self.app_lock_width, 0, wx.ALL, 5)
        hl = wx.StaticText(app_scroll, label="H:")
        hl.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(hl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_lock_height = wx.SpinCtrl(app_scroll, value=str(app_config.get("lockscreen_height", 460)), min=300, max=800, size=(80, -1))
        self.app_lock_height.SetName("Lock screen height")
        row.Add(self.app_lock_height, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        # Apply button
        apply_btn = wx.Button(app_scroll, label="Apply & Save Appearance")
        apply_btn.Bind(wx.EVT_BUTTON, self.on_apply_appearance)
        app_scroll_sizer.Add(apply_btn, 0, wx.ALL | wx.CENTER, 15)

        app_scroll.SetSizer(app_scroll_sizer)
        appearance_sizer.Add(app_scroll, 1, wx.EXPAND)
        appearance_panel.SetSizer(appearance_sizer)

        if self.config.get("developer_mode", False):
            self.add_dev_tab()
        
        self.frame.Show()

    def on_save_lock(self, event):
        code = self.lock_input.GetValue().strip()
        confirm = self.lock_confirm.GetValue().strip()

        if self.lock_enabled.IsChecked() and not code:
            self.lock_status.SetLabel("Enter a PIN or password.")
            self.api.speak("Enter a PIN or password to set.")
            return

        if code and code != confirm:
            self.lock_status.SetLabel("Codes do not match.")
            self.api.speak("Codes do not match.")
            return

        lock_type = "pin" if self.lock_type.GetSelection() == 0 else "password"
        config = lockscreen.load_config(self.api.data_dir)
        config["enabled"] = self.lock_enabled.IsChecked()
        config["lock_type"] = lock_type
        auto_lock_map = {"Never": 0, "1 min": 1, "5 min": 5, "15 min": 15, "30 min": 30}
        config["auto_lock_minutes"] = auto_lock_map.get(self.auto_lock_choice.GetStringSelection(), 0)
        if code:
            config["hash"] = lockscreen._hash(code)
        lockscreen.save_config(self.api.data_dir, config)

        self.lock_input.Clear()
        self.lock_confirm.Clear()
        self._update_lock_status_display(config)
        self.alert("Lock settings saved.", "Security")
        self.lock_status.SetLabel("Lock settings saved.")
        self.api.speak("Lock settings saved.")

    def on_clear_lock(self, event):
        if not self.confirm("Are you sure you want to disable the lock screen and clear your PIN/password?"):
            return
        config = lockscreen.load_config(self.api.data_dir)
        config["enabled"] = False
        config["hash"] = ""
        lockscreen.save_config(self.api.data_dir, config)
        self.lock_enabled.SetValue(False)
        self.lock_input.Clear()
        self.lock_confirm.Clear()
        self._update_lock_status_display(config)
        msg = "Lock code cleared and lock screen disabled."
        self.lock_status.SetLabel(msg)
        self.api.speak(msg)

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
            if self.config.get("developer_mode", False):
                self.api.terminal_output("You are already a developer.")
                return
            config = lockscreen.load_config(self.api.data_dir)
            if config.get("hash"):
                if self.frame:
                    self._show_dev_unlock_dialog(config)
                else:
                    self.api.terminal_output("Open the Settings app in GUI mode to unlock developer mode with your PIN.")
            else:
                self.easter_egg_count += 1
                taps_left = 7 - self.easter_egg_count
                if taps_left > 0:
                    self.api.terminal_output(f"{taps_left} steps away from being a developer.")
                elif taps_left == 0:
                    self._activate_developer_mode()
        else:
            self.api.terminal_output("Settings commands: 'speed <value>', 'version'")
