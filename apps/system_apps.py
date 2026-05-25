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

    def _rom_manager(self, event):
        import rom_manager
        roms = rom_manager.list_roms(self.api.data_dir)
        names = [f"{r[1].get('name', r[0])} v{r[1].get('version', '?')}" for r in roms]
        dlg = wx.SingleChoiceDialog(self, "Select ROM to activate:", "ROM Manager", names)
        dlg.SetName("ROM Manager")
        if dlg.ShowModal() == wx.ID_OK:
            idx = dlg.GetSelection()
            name = roms[idx][0]
            rom_manager.set_active_rom(self.api.data_dir, name)
            self.api.speak(f"ROM {name} activated. Restart to apply.")
        dlg.Destroy()

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
        self.dev_panel.SetName("Developer Tab")
        self.dev_panel.SetBackgroundColour(wx.Colour(5, 5, 5))
        dev_sizer = wx.BoxSizer(wx.VERTICAL)

        title = self.make_dev_setting(self.dev_panel, "Developer Options", "Developer Options")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dev_sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        info = self.make_dev_setting(self.dev_panel, "Developer options are active", "Developer Info")
        dev_sizer.Add(info, 0, wx.ALL | wx.CENTER, 5)

        self.add_separator(dev_sizer, 10, self.dev_panel)

        dev_items = [
            ("Open Data Folder", self._dev_open_data, "data"),
            ("Open Apps Folder", self._dev_open_apps, "apps"),
            ("Reload Plugins", self._dev_reload_plugins, "reload"),
            ("Edit Main Config", self._dev_edit_config, "config"),
            ("Edit Appearance Config", self._dev_edit_appearance, "appearance"),
            ("Run Diagnostics", self._dev_run_diagnostics, "diagnostics"),
        ]
        for label, handler, _ in dev_items:
            dev_sizer.Add(self.make_button(self.dev_panel, label, handler, label), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.add_separator(dev_sizer, 10, self.dev_panel)

        tool_items = [
            ("Log Viewer", self._dev_log_viewer),
            ("App Inspector", self._dev_app_inspector),
            ("Keyboard Shortcuts", self._dev_keyboard_shortcuts),
            ("Speech Lab", self._dev_speech_lab),
            ("Network Status", self._dev_network_status),
            ("Config Tree", self._dev_config_tree),
        ]
        for label, handler in tool_items:
            dev_sizer.Add(self.make_button(self.dev_panel, label, handler, label), 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self.add_separator(dev_sizer, 10, self.dev_panel)

        ffmpeg_box = wx.CheckBox(self.dev_panel, label="Force ffmpeg for sounds (disables sounddevice)")
        ffmpeg_box.SetName("Force ffmpeg")
        ffmpeg_box.SetValue(self.api.sounds.get_ffmpeg_flag())
        ffmpeg_box.SetBackgroundColour(wx.Colour(5, 5, 5))
        ffmpeg_box.SetForegroundColour(wx.Colour(200, 200, 200))
        ffmpeg_box.Bind(wx.EVT_CHECKBOX, lambda evt: self.api.sounds.set_ffmpeg_flag(ffmpeg_box.GetValue()))
        dev_sizer.Add(ffmpeg_box, 0, wx.ALL, 8)

        self.add_separator(dev_sizer, 10, self.dev_panel)

        # Danger Zone
        danger_label = self.make_dev_setting(self.dev_panel, "Danger Zone", "Danger Zone")
        danger_label.SetForegroundColour(wx.Colour(255, 80, 80))
        danger_label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dev_sizer.Add(danger_label, 0, wx.ALL | wx.CENTER, 8)

        reset_btn = wx.Button(self.dev_panel, label="Reset All Configs (factory defaults)")
        reset_btn.SetName("Reset All Configs")
        reset_btn.SetBackgroundColour(wx.Colour(60, 0, 0))
        reset_btn.SetForegroundColour(wx.Colour(200, 100, 100))
        reset_btn.Bind(wx.EVT_BUTTON, self._dev_reset_configs)
        dev_sizer.Add(reset_btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        disable_btn = wx.Button(self.dev_panel, label="Disable Developer Options")
        disable_btn.SetName("Disable Developer Options")
        disable_btn.SetBackgroundColour(wx.Colour(50, 0, 0))
        disable_btn.SetForegroundColour(wx.Colour(180, 100, 100))
        disable_btn.Bind(wx.EVT_BUTTON, self.on_disable_dev_mode)
        dev_sizer.Add(disable_btn, 0, wx.EXPAND | wx.ALL, 15)

        self.dev_panel.SetSizer(dev_sizer)
        self.notebook.AddPage(self.dev_panel, "Developer")
        self.api.speak("Developer tab added.")

    def _dev_open_data(self, event):
        self.api.launch_app("FileExplorerApp", path=self.api.data_dir)

    def _dev_open_apps(self, event):
        apps_path = os.path.join(os.getcwd(), "apps")
        self.api.launch_app("FileExplorerApp", path=apps_path)

    def _dev_reload_plugins(self, event):
        try:
            desktop = self.api.desktop
            desktop.load_plugins()
            desktop.refresh_app_list()
            self.api.speak("Plugins reloaded.")
        except Exception as e:
            self.api.speak(f"Reload failed: {e}")

    def _dev_edit_config(self, event):
        path = os.path.join(self.api.data_dir, "pyos_config.json")
        self.api.launch_app("TextEditorApp", filepath=path)

    def _dev_edit_appearance(self, event):
        path = config_manager.get_appearance_path(self.api.data_dir)
        self.api.launch_app("TextEditorApp", filepath=path)

    def _dev_run_diagnostics(self, event):
        import sys as _sys, io as _io
        try:
            old_stdout = _sys.stdout
            _sys.stdout = buf = _io.StringIO()
            import diagnose_startup
            diagnose_startup.diagnose()
            _sys.stdout = old_stdout
            log_path = os.path.join(os.getcwd(), "startup_error.log")
            if os.path.exists(log_path):
                with open(log_path) as f:
                    content = f.read()
                self.show_info(content.strip() or "Diagnostics completed.", "Diagnostics")
            else:
                self.show_info("Diagnostics completed. No errors found.", "Diagnostics")
        except Exception as e:
            self.show_error(f"Diagnostics failed: {e}")

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
        dlg.SetName("Developer Unlock Dialog")
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetName("Developer Unlock Panel")
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Enter your lock code")
        title.SetName("Unlock Title")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        status = wx.StaticText(panel, label="")
        status.SetName("Unlock Status")
        status.SetForegroundColour(wx.Colour(255, 80, 80))
        sizer.Add(status, 0, wx.ALL | wx.CENTER, 5)

        pin_buffer = [""]

        if config.get("lock_type") == "pin":
            display = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_CENTER, size=(150, 40))
            display.SetName("PIN Display")
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
                btn.SetName(label if label else "Backspace")
                btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
                if action == "bs":
                    btn.Bind(wx.EVT_BUTTON, lambda evt: on_backspace())
                elif action:
                    btn.Bind(wx.EVT_BUTTON, lambda evt, d=action: on_digit(d))
                grid.Add(btn, 0, wx.EXPAND)
            sizer.Add(grid, 0, wx.ALL | wx.CENTER, 10)
        else:
            pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER, size=(200, 30))
            pwd_input.SetName("Password Input")
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
        unlock_btn.SetName("Unlock Button")
        unlock_btn.Bind(wx.EVT_BUTTON, on_submit)
        sizer.Add(unlock_btn, 0, wx.ALL | wx.CENTER, 10)

        cancel_btn = wx.Button(panel, label="Cancel")
        cancel_btn.SetName("Cancel Button")
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
        c["wallpaper_path"] = self.wallpaper_path_input.GetValue().strip()
        style_idx = self.wallpaper_style_choice.GetSelection()
        style_map = ["stretch", "tile", "center", "fit"]
        c["wallpaper_style"] = style_map[style_idx] if 0 <= style_idx < len(style_map) else "stretch"
        config_manager.save_appearance_config(self.api.data_dir, c)
        self.api.speak("Appearance settings saved. Restart the desktop to see changes.")
        self.show_info("Appearance settings saved. Restart the desktop to see changes.")

    def _reset_appearance_section(self, section, sizer, parent, old_config):
        defaults = {
            "desktop_bg": "#000000", "desktop_button_bg": "#282828", "desktop_button_fg": "#FFFFFF",
            "desktop_header": "PyOS Desktop", "desktop_header_color": "#FFFFFF",
            "desktop_header_font_size": 18, "desktop_button_font_size": 16,
            "desktop_button_spacing": 5, "desktop_greeting": "Welcome to PyOS. Use Tab to navigate through apps, and press Enter to launch.",
            "desktop_scroll_rate": 20, "desktop_width": 800, "desktop_height": 600,
            "wallpaper_path": "", "wallpaper_style": "stretch",
            "lockscreen_bg": "#000000", "lockscreen_title_color": "#FFFFFF",
            "lockscreen_title_text": "Lock Screen", "lockscreen_title_font_size": 18,
            "lockscreen_mode_color": "#B4B4B4", "lockscreen_status_color": "#FF5050",
            "lockscreen_input_bg": "#1E1E1E", "lockscreen_input_fg": "#FFFFFF",
            "lockscreen_display_font_size": 20, "lockscreen_input_font_size": 14,
            "lockscreen_pin_font_size": 14, "lockscreen_mask_char": "*",
            "lockscreen_width": 350, "lockscreen_height": 460,
        }
        keys = []
        if section == "desktop":
            keys = ["desktop_bg", "desktop_button_bg", "desktop_button_fg", "desktop_header",
                    "desktop_header_color", "desktop_header_font_size", "desktop_button_font_size",
                    "desktop_button_spacing", "desktop_greeting", "desktop_width", "desktop_height"]
        elif section == "wallpaper":
            keys = ["wallpaper_path", "wallpaper_style"]
        elif section == "lockscreen":
            keys = [k for k in defaults if k.startswith("lockscreen")]
        ac = config_manager.load_appearance_config(self.api.data_dir)
        for k in keys:
            ac[k] = defaults.get(k, ac.get(k))
        config_manager.save_appearance_config(self.api.data_dir, ac)
        self.api.speak(f"{section.capitalize()} section reset to defaults. Apply to save changes.")

    def _on_wallpaper_browse(self, event):
        wildcard = "Images (*.bmp;*.jpg;*.jpeg;*.png;*.gif)|*.bmp;*.jpg;*.jpeg;*.png;*.gif"
        dlg = wx.FileDialog(self.frame, "Choose a wallpaper image", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.wallpaper_path_input.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_wallpaper_clear(self, event):
        self.wallpaper_path_input.SetValue("")
        self.api.speak("Wallpaper cleared. Apply to save.")

    # --- Developer Tool Dialogs ---

    def _dev_log_viewer(self, event):
        dlg = wx.Dialog(self.frame, title="Log Viewer", size=(600, 450))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Log Viewer")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        log_paths = [
            os.path.join(os.getcwd(), "startup_error.log"),
            os.path.join(self.api.data_dir, "startup_error.log"),
        ]
        content = ""
        for p in log_paths:
            if os.path.exists(p):
                try:
                    with open(p) as f:
                        content = f.read()
                    break
                except: pass

        tc = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL, size=(560, 300))
        tc.SetName("Log Content")
        tc.SetValue(content if content else "(No log file found)")
        tc.SetBackgroundColour(wx.Colour(15, 15, 15))
        tc.SetForegroundColour(wx.Colour(200, 200, 200))
        tc.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(tc, 1, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        refresh_btn = wx.Button(panel, label="Refresh")
        refresh_btn.Bind(wx.EVT_BUTTON, lambda evt: self._dev_log_refresh(tc, log_paths))
        btn_row.Add(refresh_btn, 0, wx.RIGHT, 10)

        clear_btn = wx.Button(panel, label="Clear Log")
        clear_btn.Bind(wx.EVT_BUTTON, lambda evt: self._dev_log_clear(tc, log_paths))
        btn_row.Add(clear_btn, 0, wx.RIGHT, 10)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        btn_row.Add(close_btn, 0)
        sizer.Add(btn_row, 0, wx.CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_log_refresh(self, tc, log_paths):
        content = ""
        for p in log_paths:
            if os.path.exists(p):
                try:
                    with open(p) as f:
                        content = f.read()
                    break
                except: pass
        tc.SetValue(content if content else "(No log file found)")

    def _dev_log_clear(self, tc, log_paths):
        for p in log_paths:
            if os.path.exists(p):
                try:
                    open(p, "w").close()
                except: pass
        tc.SetValue("(Log cleared)")
        self.api.speak("Log cleared.")

    def _dev_app_inspector(self, event):
        dlg = wx.Dialog(self.frame, title="App Inspector", size=(550, 400))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="App Inspector")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(510, 280))
        list_ctrl.SetName("App Inspector List")
        list_ctrl.SetBackgroundColour(wx.Colour(15, 15, 15))
        list_ctrl.SetForegroundColour(wx.Colour(200, 200, 200))
        list_ctrl.AppendColumn("App Name", width=150)
        list_ctrl.AppendColumn("File", width=120)
        list_ctrl.AppendColumn("Hotkey", width=100)
        list_ctrl.AppendColumn("Pinned", width=80)

        desktop = self.api.desktop
        hidden = desktop.sys_config.get("hidden_apps", [])
        hotkeys = {v: k for k, v in desktop.sys_config.get("app_hotkeys", {}).items()}
        for app in desktop.apps:
            fname = getattr(app, "_file", "") or ""
            hk = hotkeys.get(app.name, "")
            pinned = "No" if app.name in hidden else "Yes"
            idx = list_ctrl.Append([app.name, fname, hk, pinned])

        sizer.Add(list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(close_btn, 0, wx.CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_keyboard_shortcuts(self, event):
        dlg = wx.Dialog(self.frame, title="Keyboard Shortcuts", size=(450, 350))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Keyboard Shortcuts")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(400, 200))
        list_ctrl.SetName("Shortcuts List")
        list_ctrl.SetBackgroundColour(wx.Colour(15, 15, 15))
        list_ctrl.SetForegroundColour(wx.Colour(200, 200, 200))
        list_ctrl.AppendColumn("Hotkey", width=150)
        list_ctrl.AppendColumn("App", width=200)

        desktop = self.api.desktop
        hotkeys = desktop.sys_config.get("app_hotkeys", {})
        for combo, app_name in sorted(hotkeys.items()):
            list_ctrl.Append([combo, app_name])

        sizer.Add(list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(close_btn, 0, wx.CENTER | wx.BOTTOM, 5)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_speech_lab(self, event):
        dlg = wx.Dialog(self.frame, title="Speech Lab", size=(450, 400))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Speech Lab")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        engine = self.api.engine
        mode = getattr(engine, "get_mode", lambda: "unknown")()
        rate = getattr(engine, "get_rate", lambda: 0)()
        status_text = f"Engine: {mode.upper()}  |  Rate: {rate}"
        status_lbl = wx.StaticText(panel, label=status_text)
        status_lbl.SetForegroundColour(wx.Colour(180, 180, 255))
        sizer.Add(status_lbl, 0, wx.ALL | wx.CENTER, 5)

        try:
            voices = getattr(engine, "get_sapi_voices", lambda: [])()
            if voices:
                voice_lbl = wx.StaticText(panel, label="Available SAPI voices:")
                voice_lbl.SetForegroundColour(wx.Colour(200, 200, 200))
                sizer.Add(voice_lbl, 0, wx.ALL, 10)

                voice_list = wx.ListBox(panel, size=(400, 120), choices=voices)
                voice_list.SetName("Voices List")
                voice_list.SetBackgroundColour(wx.Colour(15, 15, 15))
                voice_list.SetForegroundColour(wx.Colour(200, 200, 200))
                sizer.Add(voice_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

                def on_test_voice(evt):
                    sel = voice_list.GetSelection()
                    if sel >= 0:
                        getattr(engine, "set_sapi_voice", lambda i: None)(sel)
                        self.api.speak(f"Testing voice: {voices[sel]}")
                test_v_btn = wx.Button(panel, label="Test Selected Voice")
                test_v_btn.Bind(wx.EVT_BUTTON, on_test_voice)
                sizer.Add(test_v_btn, 0, wx.ALL | wx.CENTER, 8)
        except Exception:
            pass

        test_sizer = wx.BoxSizer(wx.HORIZONTAL)
        test_input = wx.TextCtrl(panel, size=(300, -1), style=wx.TE_PROCESS_ENTER)
        test_input.SetName("Speech Test Input")
        test_input.SetHint("Type text to speak")
        test_input.SetBackgroundColour(wx.Colour(30, 30, 30))
        test_input.SetForegroundColour(wx.Colour(255, 255, 255))
        test_sizer.Add(test_input, 1, wx.RIGHT, 8)
        test_btn = wx.Button(panel, label="Speak")
        test_btn.Bind(wx.EVT_BUTTON, lambda evt: self.api.speak(test_input.GetValue().strip() or "Hello, this is a speech test."))
        test_input.Bind(wx.EVT_TEXT_ENTER, lambda evt: self.api.speak(test_input.GetValue().strip() or "Hello, this is a speech test."))
        test_sizer.Add(test_btn, 0)
        sizer.Add(test_sizer, 0, wx.EXPAND | wx.ALL, 10)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(close_btn, 0, wx.CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_network_status(self, event):
        dlg = wx.Dialog(self.frame, title="Network Status", size=(400, 250))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Network Status")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        net = self.api.network
        running = getattr(net, "running", False)
        status_lbl = wx.StaticText(panel, label=f"Service: {'RUNNING' if running else 'STOPPED'}")
        status_lbl.SetForegroundColour(wx.Colour(100, 255, 100) if running else wx.Colour(255, 100, 100))
        status_lbl.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(status_lbl, 0, wx.ALL | wx.CENTER, 10)

        if running:
            toggle_btn = wx.Button(panel, label="Stop Network Service")
            toggle_btn.Bind(wx.EVT_BUTTON, lambda evt: (getattr(net, "stop", lambda: None)(), status_lbl.SetLabel("Service: STOPPED"), status_lbl.SetForegroundColour(wx.Colour(255, 100, 100)), evt.GetEventObject().SetLabel("Start Network Service"), dlg.Close(), self.api.speak("Network service stopped.")))
        else:
            toggle_btn = wx.Button(panel, label="Start Network Service")
            toggle_btn.Bind(wx.EVT_BUTTON, lambda evt: (getattr(net, "start", lambda: None)(), status_lbl.SetLabel("Service: RUNNING"), status_lbl.SetForegroundColour(wx.Colour(100, 255, 100)), evt.GetEventObject().SetLabel("Stop Network Service"), dlg.Close(), self.api.speak("Network service started.")))
        sizer.Add(toggle_btn, 0, wx.ALL | wx.CENTER, 8)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(close_btn, 0, wx.CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_config_tree(self, event):
        dlg = wx.Dialog(self.frame, title="Config Tree", size=(500, 400))
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label="Config Tree")
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 10)

        tree = wx.TreeCtrl(panel, style=wx.TR_DEFAULT_STYLE, size=(460, 280))
        tree.SetName("Config Tree")
        tree.SetBackgroundColour(wx.Colour(15, 15, 15))
        tree.SetForegroundColour(wx.Colour(200, 200, 200))
        root = tree.AddRoot("Configs")

        config_files = [
            ("pyos_config.json", self.api.data_dir),
            ("appearance_config.json", self.api.data_dir),
            ("speech_config.json", self.api.data_dir),
            ("device_config.json", self.api.data_dir),
            ("lock_config.json", self.api.data_dir),
        ]
        import json
        for fname, dir_path in config_files:
            fpath = os.path.join(dir_path, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                except:
                    data = "(unreadable)"
                node = tree.AppendItem(root, fname)
                if isinstance(data, dict):
                    for k, v in data.items():
                        v_str = str(v)[:60]
                        tree.AppendItem(node, f"{k}: {v_str}")
                else:
                    tree.AppendItem(node, str(data)[:80])
            else:
                tree.AppendItem(root, f"{fname} (not found)")
        tree.Expand(root)

        sizer.Add(tree, 1, wx.EXPAND | wx.ALL, 10)

        close_btn = wx.Button(panel, label="Close")
        close_btn.Bind(wx.EVT_BUTTON, lambda evt: dlg.Close())
        sizer.Add(close_btn, 0, wx.CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        dlg.ShowModal()
        dlg.Destroy()

    def _dev_reset_configs(self, event):
        if not self.confirm_delete("ALL configuration files (config, appearance, lock, speech, device). This cannot be undone!"):
            return
        import json
        config_files = ["pyos_config.json", "appearance_config.json", "speech_config.json", "device_config.json", "lock_config.json"]
        deleted = 0
        for fname in config_files:
            fpath = os.path.join(self.api.data_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                    deleted += 1
                except: pass
        self.api.speak(f"Reset complete. {deleted} config files deleted. Restart the desktop to regenerate defaults.")

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
                self.api.speak("Git pull failed; attempting full clone...")
                self._fallback_clone()

            # 2. Update dependencies
            pip_result = subprocess.run(["pip", "install", "-r", "requirements.txt"], capture_output=True, text=True)
            
            if pip_result.returncode == 0:
                self.api.speak("System updated successfully.")
            else:
                self.api.speak("Dependencies failed to update.")
        
        except Exception:
            self.api.speak("An error occurred during update.")

    def _fallback_clone(self):
        try:
            url_result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, cwd=os.getcwd())
            remote_url = url_result.stdout.strip() if url_result.returncode == 0 else ""
            if not remote_url or "techmaster300" in remote_url:
                remote_url = "https://github.com/tech-master33/py-os.git"

            parent = os.path.dirname(os.getcwd())
            temp_dir = os.path.join(parent, "py-os-update-temp")

            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.api.speak("Cloning repository...")
            clone_result = subprocess.run(["git", "clone", remote_url, temp_dir], capture_output=True, text=True)
            if clone_result.returncode != 0:
                self.api.speak("Clone failed. Update aborted.")
                return

            for item in os.listdir(temp_dir):
                src = os.path.join(temp_dir, item)
                dst = os.path.join(os.getcwd(), item)
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst, ignore_dangling_symlinks=True)
                else:
                    shutil.copy2(src, dst)

            shutil.rmtree(temp_dir, ignore_errors=True)
            self.api.speak("Clone complete; repository restored.")
        except Exception as e:
            self.api.speak(f"Clone fallback failed: {e}")

    def run(self):
        self.frame = wx.Frame(None, title="Settings", size=(500, 600))
        self.notebook = wx.Notebook(self.frame)
        self.notebook.SetName("Settings Notebook")

        # --- General Tab ---
        gen_panel = self.make_panel(self.notebook, "General Tab")
        gen_sizer = self.vbox()
        self.notebook.AddPage(gen_panel, "General")

        title = wx.StaticText(gen_panel, label="System Settings")
        title.SetName("System Settings Title")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        gen_sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        self.version_btn = self.make_button(gen_panel, "Version: 2026.05.22 (Click for details)", self.on_version_click, "Version Button")
        gen_sizer.Add(self.version_btn, 0, wx.ALL | wx.CENTER, 5)

        import sys as _sys
        py_ver = f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"
        wx_ver = wx.VERSION_STRING
        info = self.make_static(gen_panel, f"Python {py_ver}  |  wxPython {wx_ver}", "System Info")
        info.SetForegroundColour(wx.Colour(140, 140, 140))
        gen_sizer.Add(info, 0, wx.ALL | wx.CENTER, 2)

        gen_sizer.Add(self.make_static(gen_panel, "Language:", "Language Label"), 0, wx.ALL, 10)

        langs = translation.available_languages()
        lang_codes = list(langs.keys())
        lang_names = list(langs.values())
        self.lang_choice = self.make_choice(gen_panel, lang_names, "Language Selector")
        current_lang = self.config.get("language", "en")
        if current_lang in lang_codes:
            self.lang_choice.SetSelection(lang_codes.index(current_lang))
        else:
            self.lang_choice.SetSelection(0)
        self.lang_choice.Bind(wx.EVT_CHOICE, self.on_language_change)
        gen_sizer.Add(self.lang_choice, 0, wx.EXPAND | wx.ALL, 8)

        gen_sizer.Add(self.make_static(gen_panel, "Sound Theme:", "Theme Label"), 0, wx.ALL, 10)

        themes = self.api.sounds.get_available_themes()
        self.theme_choice = self.make_choice(gen_panel, themes if themes else ["Modern"], "Theme Selector")
        current_theme = self.api.sounds.current_theme
        if current_theme in themes: self.theme_choice.SetSelection(themes.index(current_theme))
        else: self.theme_choice.SetSelection(0)
        self.theme_choice.Bind(wx.EVT_CHOICE, self.on_theme_preview)
        gen_sizer.Add(self.theme_choice, 0, wx.EXPAND | wx.ALL, 8)

        gen_sizer.Add(self.make_button(gen_panel, "Check for Updates", self.check_updates, "Update Button"), 0, wx.EXPAND | wx.ALL, 8)

        gen_sizer.Add(self.make_button(gen_panel, "ROM Manager", self._rom_manager, "ROM Manager"), 0, wx.EXPAND | wx.ALL, 8)

        gen_panel.SetSizer(gen_sizer)

        # --- Speech Tab ---
        speech_panel = self.make_panel(self.notebook, "Speech Tab")
        speech_sizer = self.vbox()
        self.notebook.AddPage(speech_panel, "Speech")

        speech_sizer.Add(self.make_static(speech_panel, "Speech Engine:", "Speech Engine Label"), 0, wx.ALL, 10)
        self.speech_modes = [("Auto", "auto"), ("NVDA", "nvda"), ("SAPI", "sapi")]
        self.speech_choice = self.make_choice(speech_panel, [m[0] for m in self.speech_modes], "Speech Engine Selector")
        current_mode = getattr(self.api.engine, "get_mode", lambda: "auto")()
        idx = next((i for i, m in enumerate(self.speech_modes) if m[1] == current_mode), 0)
        self.speech_choice.SetSelection(idx)
        self.speech_choice.Bind(wx.EVT_CHOICE, self.on_speech_mode_change)
        speech_sizer.Add(self.speech_choice, 0, wx.EXPAND | wx.ALL, 8)

        speech_sizer.Add(self.make_static(speech_panel, "Voice Speed:", "Speed Label"), 0, wx.ALL, 10)
        current_rate = getattr(self.api.engine, "get_rate", lambda: 200)()
        self.speed_slider = self.make_slider(speech_panel, current_rate, 50, 400, "Speed Slider")
        self.speed_slider.Bind(wx.EVT_SLIDER, self.on_speed_change)
        speech_sizer.Add(self.speed_slider, 0, wx.EXPAND | wx.ALL, 10)

        voice_list = getattr(self.api.engine, "get_sapi_voices", lambda: [])()
        if voice_list:
            speech_sizer.Add(self.make_static(speech_panel, "SAPI Voice:", "Voice Label"), 0, wx.ALL, 10)
            self.voice_choice = self.make_choice(speech_panel, voice_list, "Voice Selector")
            current_voice = getattr(self.api.engine, "_sapi_voice_index", 0)
            if 0 <= current_voice < len(voice_list):
                self.voice_choice.SetSelection(current_voice)
            self.voice_choice.Bind(wx.EVT_CHOICE, self.on_voice_change)
            speech_sizer.Add(self.voice_choice, 0, wx.EXPAND | wx.ALL, 8)

        speech_panel.SetSizer(speech_sizer)

        # --- Audio Tab ---
        audio_panel = self.make_panel(self.notebook, "Audio Tab")
        audio_sizer = self.vbox()
        self.notebook.AddPage(audio_panel, "Audio")

        if HAS_SOUNDDEVICE:
            audio_sizer.Add(self.make_static(audio_panel, "Input Device (Microphone):", "Input Device Label"), 0, wx.ALL, 8)
            self.input_entries = self.get_input_devices()
            input_labels = [self._device_label(d) for d in self.input_entries] or ["Default"]
            self.input_choice = self.make_choice(audio_panel, input_labels, "Input Device")
            audio_sizer.Add(self.input_choice, 0, wx.EXPAND | wx.ALL, 8)

            audio_sizer.Add(self.make_static(audio_panel, "Output Device (Speaker):", "Output Device Label"), 0, wx.ALL, 8)
            self.output_entries = self.get_output_devices()
            output_labels = [self._device_label(d) for d in self.output_entries] or ["Default"]
            self.output_choice = self.make_choice(audio_panel, output_labels, "Output Device")
            audio_sizer.Add(self.output_choice, 0, wx.EXPAND | wx.ALL, 8)

            audio_sizer.Add(self.make_button(audio_panel, "Test Audio", self.on_test_audio, "Test Audio"), 0, wx.EXPAND | wx.ALL, 8)
        audio_panel.SetSizer(audio_sizer)

        # --- Security Tab ---
        sec_panel = self.make_panel(self.notebook, "Security Tab")
        sec_sizer = self.vbox()
        self.notebook.AddPage(sec_panel, "Security")

        sec_title = wx.StaticText(sec_panel, label="Lock Screen Settings")
        sec_title.SetName("Lock Screen Settings Title")
        sec_title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sec_sizer.Add(sec_title, 0, wx.ALL | wx.CENTER, 15)

        lock_config = lockscreen.load_config(self.api.data_dir)

        self.lock_status_display = self.make_static(sec_panel, "", "Lock Status Display")
        sec_sizer.Add(self.lock_status_display, 0, wx.ALL | wx.CENTER, 5)
        self._update_lock_status_display(lock_config)

        self.lock_enabled = self.make_checkbox(sec_panel, "Enable lock screen on startup", None, "")
        self.lock_enabled.SetValue(lock_config.get("enabled", False))
        sec_sizer.Add(self.lock_enabled, 0, wx.ALL, 10)

        sec_sizer.Add(self.make_static(sec_panel, "Lock type:", "Lock Type Label"), 0, wx.LEFT | wx.RIGHT, 10)
        self.lock_type = self.make_choice(sec_panel, ["PIN", "Password"], "Lock Type")
        self.lock_type.SetSelection(0 if lock_config.get("lock_type") == "pin" else 1)
        sec_sizer.Add(self.lock_type, 0, wx.EXPAND | wx.ALL, 10)

        sec_sizer.Add(self.make_static(sec_panel, "Set new PIN or password:", "Code Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lock_input = self.make_textctrl(sec_panel, name="Lock Input")
        sec_sizer.Add(self.lock_input, 0, wx.EXPAND | wx.ALL, 10)

        sec_sizer.Add(self.make_static(sec_panel, "Confirm:", "Confirm Label"), 0, wx.LEFT | wx.RIGHT, 10)
        self.lock_confirm = self.make_textctrl(sec_panel, name="Lock Confirm")
        sec_sizer.Add(self.lock_confirm, 0, wx.EXPAND | wx.ALL, 10)

        sec_sizer.Add(self.make_button(sec_panel, "Save Lock Settings", self.on_save_lock, "Save Lock"), 0, wx.ALL | wx.CENTER, 10)

        sec_sizer.Add(self.make_static(sec_panel, "Auto-lock after:", "Auto Lock Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.auto_lock_choice = self.make_choice(sec_panel, ["Never", "1 min", "5 min", "15 min", "30 min"], "Auto Lock")
        auto_val = lock_config.get("auto_lock_minutes", 0)
        auto_map = {0: 0, 1: 1, 5: 2, 15: 3, 30: 4}
        self.auto_lock_choice.SetSelection(auto_map.get(auto_val, 0))
        sec_sizer.Add(self.auto_lock_choice, 0, wx.EXPAND | wx.ALL, 10)

        self.lock_status = self.make_static(sec_panel, "", "Lock Status")
        sec_sizer.Add(self.lock_status, 0, wx.ALL | wx.CENTER, 5)

        sec_sizer.Add(self.make_button(sec_panel, "Disable & Clear Lock Code", self.on_clear_lock, "Clear Lock"), 0, wx.ALL | wx.CENTER, 5)

        sec_panel.SetSizer(sec_sizer)

        # --- Appearance Tab ---
        appearance_panel = self.make_panel(self.notebook, "Appearance Tab")
        appearance_sizer = self.vbox()
        self.notebook.AddPage(appearance_panel, "Appearance")

        app_scroll = wx.ScrolledWindow(appearance_panel, style=wx.VSCROLL)
        app_scroll.SetName("Appearance Scroll")
        app_scroll.SetScrollRate(0, 20)
        app_scroll.SetBackgroundColour(wx.Colour(0, 0, 0))
        app_scroll_sizer = self.vbox()
        app_config = config_manager.load_appearance_config(self.api.data_dir)

        def add_color_row(parent, sizer, label, config_key, default_color):
            row = self.hbox()
            row.Add(self.make_static(parent, label, label, size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            ctrl = wx.ColourPickerCtrl(parent, colour=wx.Colour(app_config.get(config_key, default_color)))
            ctrl.SetName(label)
            row.Add(ctrl, 0, wx.ALL, 5)
            sizer.Add(row, 0, wx.EXPAND)
            return ctrl

        # Desktop section
        desk_label = wx.StaticText(app_scroll, label="Desktop")
        desk_label.SetName("Desktop Section")
        desk_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        desk_label.SetForegroundColour(wx.Colour(255, 255, 255))
        app_scroll_sizer.Add(desk_label, 0, wx.ALL | wx.CENTER, 10)

        self.app_desk_bg = add_color_row(app_scroll, app_scroll_sizer, "Background:", "desktop_bg", "#000000")
        self.app_desk_btn_bg = add_color_row(app_scroll, app_scroll_sizer, "Button background:", "desktop_button_bg", "#282828")
        self.app_desk_btn_fg = add_color_row(app_scroll, app_scroll_sizer, "Button text:", "desktop_button_fg", "#FFFFFF")

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Header text:", "Header Text Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_header = self.make_textctrl(app_scroll, name="Header text", value=app_config.get("desktop_header", "PyOS Desktop"), size=(200, -1))
        self.app_desk_header.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_desk_header.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_desk_header, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        self.app_desk_header_color = add_color_row(app_scroll, app_scroll_sizer, "Header color:", "desktop_header_color", "#FFFFFF")

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Header font size:", "Header Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_header_fs = self.make_spinctrl(app_scroll, value=app_config.get("desktop_header_font_size", 18), min_v=12, max_v=36, name="Header font size")
        row.Add(self.app_desk_header_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Button spacing:", "Button Spacing Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_spacing = self.make_spinctrl(app_scroll, value=app_config.get("desktop_button_spacing", 5), min_v=0, max_v=30, name="Button spacing")
        row.Add(self.app_desk_spacing, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Greeting text:", "Greeting Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_greeting = self.make_textctrl(app_scroll, name="Greeting text", value=app_config.get("desktop_greeting", "Welcome to PyOS. Use Tab to navigate through apps, and press Enter to launch."), size=(250, -1))
        self.app_desk_greeting.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_desk_greeting.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_desk_greeting, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Button font size:", "Button Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_desk_font_size = self.make_spinctrl(app_scroll, value=app_config.get("desktop_button_font_size", 16), min_v=10, max_v=32, name="Button font size")
        row.Add(self.app_desk_font_size, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Window size (W x H):", "Window Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        width_label = self.make_static(app_scroll, "W:", "Width Label")
        width_label.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(width_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_desk_width = self.make_spinctrl(app_scroll, value=app_config.get("desktop_width", 800), min_v=600, max_v=1600, name="Desktop width")
        row.Add(self.app_desk_width, 0, wx.ALL, 5)
        height_label = self.make_static(app_scroll, "H:", "Height Label")
        height_label.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(height_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_desk_height = self.make_spinctrl(app_scroll, value=app_config.get("desktop_height", 600), min_v=400, max_v=1200, name="Desktop height")
        row.Add(self.app_desk_height, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        reset_desk = self.make_button(app_scroll, "Reset Desktop Section", lambda evt: self._reset_appearance_section("desktop", app_scroll_sizer, app_scroll, app_config), "Reset Desktop")
        app_scroll_sizer.Add(reset_desk, 0, wx.CENTER | wx.TOP, 5)

        # Wallpaper section
        self.add_separator(app_scroll_sizer, 10, app_scroll)

        wall_label = wx.StaticText(app_scroll, label="Wallpaper")
        wall_label.SetName("Wallpaper Section")
        wall_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        wall_label.SetForegroundColour(wx.Colour(255, 255, 255))
        app_scroll_sizer.Add(wall_label, 0, wx.ALL | wx.CENTER, 10)

        wall_row = self.hbox()
        wall_path_label = self.make_static(app_scroll, "Path:", "Wallpaper Path Label", size=(180, -1))
        wall_row.Add(wall_path_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.wallpaper_path_input = self.make_textctrl(app_scroll, name="Wallpaper Path", value=app_config.get("wallpaper_path", ""), size=(200, -1))
        self.wallpaper_path_input.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.wallpaper_path_input.SetForegroundColour(wx.Colour(255, 255, 255))
        wall_row.Add(self.wallpaper_path_input, 0, wx.ALL, 5)
        app_scroll_sizer.Add(wall_row, 0, wx.EXPAND)

        wall_btn_row = self.hbox()
        wall_browse = self.make_button(app_scroll, "Browse...", self._on_wallpaper_browse, "Browse Wallpaper")
        wall_btn_row.Add(wall_browse, 0, wx.ALL, 5)
        wall_clear = self.make_button(app_scroll, "Clear", self._on_wallpaper_clear, "Clear Wallpaper")
        wall_btn_row.Add(wall_clear, 0, wx.ALL, 5)
        app_scroll_sizer.Add(wall_btn_row, 0, wx.CENTER)

        wall_style_row = self.hbox()
        wall_style_row.Add(self.make_static(app_scroll, "Style:", "Wallpaper Style Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.wallpaper_style_choice = self.make_choice(app_scroll, ["Stretch", "Tile", "Center", "Fit"], "Wallpaper Style")
        current_style = app_config.get("wallpaper_style", "stretch")
        style_map = {"stretch": 0, "tile": 1, "center": 2, "fit": 3}
        self.wallpaper_style_choice.SetSelection(style_map.get(current_style, 0))
        wall_style_row.Add(self.wallpaper_style_choice, 0, wx.ALL, 5)
        app_scroll_sizer.Add(wall_style_row, 0, wx.EXPAND)

        reset_wall = self.make_button(app_scroll, "Reset Wallpaper Section", lambda evt: self._reset_appearance_section("wallpaper", app_scroll_sizer, app_scroll, app_config), "Reset Wallpaper")
        app_scroll_sizer.Add(reset_wall, 0, wx.CENTER | wx.TOP, 5)

        # Lock screen section
        self.add_separator(app_scroll_sizer, 10, app_scroll)

        lock_label = wx.StaticText(app_scroll, label="Lock Screen")
        lock_label.SetName("Lock Screen Section")
        lock_label.SetFont(wx.Font(13, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        lock_label.SetForegroundColour(wx.Colour(255, 255, 255))
        app_scroll_sizer.Add(lock_label, 0, wx.ALL | wx.CENTER, 10)

        self.app_lock_bg = add_color_row(app_scroll, app_scroll_sizer, "Background:", "lockscreen_bg", "#000000")
        self.app_lock_title = add_color_row(app_scroll, app_scroll_sizer, "Title color:", "lockscreen_title_color", "#FFFFFF")
        self.app_lock_mode = add_color_row(app_scroll, app_scroll_sizer, "Mode label:", "lockscreen_mode_color", "#B4B4B4")
        self.app_lock_status_color = add_color_row(app_scroll, app_scroll_sizer, "Status color:", "lockscreen_status_color", "#FF5050")
        self.app_lock_input_bg = add_color_row(app_scroll, app_scroll_sizer, "Input background:", "lockscreen_input_bg", "#1E1E1E")
        self.app_lock_input_fg = add_color_row(app_scroll, app_scroll_sizer, "Input text:", "lockscreen_input_fg", "#FFFFFF")

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Title text:", "Title Text Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_title_text = self.make_textctrl(app_scroll, name="Lock screen title text", value=app_config.get("lockscreen_title_text", "Lock Screen"), size=(200, -1))
        self.app_lock_title_text.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_lock_title_text.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_lock_title_text, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Title font size:", "Title Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_title_fs = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_title_font_size", 18), min_v=12, max_v=36, name="Lock screen title font size")
        row.Add(self.app_lock_title_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Display font size:", "Display Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_disp_fs = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_display_font_size", 20), min_v=12, max_v=36, name="Lock screen display font size")
        row.Add(self.app_lock_disp_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Input font size:", "Input Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_input_fs = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_input_font_size", 14), min_v=10, max_v=24, name="Lock screen input font size")
        row.Add(self.app_lock_input_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "PIN pad font size:", "PIN Font Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_pin_fs = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_pin_font_size", 14), min_v=10, max_v=24, name="PIN pad font size")
        row.Add(self.app_lock_pin_fs, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Mask character:", "Mask Char Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.app_lock_mask = self.make_textctrl(app_scroll, name="Mask character", value=app_config.get("lockscreen_mask_char", "*"), size=(40, -1))
        self.app_lock_mask.SetMaxLength(1)
        self.app_lock_mask.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.app_lock_mask.SetForegroundColour(wx.Colour(255, 255, 255))
        row.Add(self.app_lock_mask, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        row = self.hbox()
        row.Add(self.make_static(app_scroll, "Dialog size (W x H):", "Dialog Size Label", size=(180, -1)), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        wl = self.make_static(app_scroll, "W:", "Lock Width Label")
        wl.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(wl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_lock_width = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_width", 350), min_v=250, max_v=800, name="Lock screen width")
        row.Add(self.app_lock_width, 0, wx.ALL, 5)
        hl = self.make_static(app_scroll, "H:", "Lock Height Label")
        hl.SetForegroundColour(wx.Colour(200, 200, 200))
        row.Add(hl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.app_lock_height = self.make_spinctrl(app_scroll, value=app_config.get("lockscreen_height", 460), min_v=300, max_v=800, name="Lock screen height")
        row.Add(self.app_lock_height, 0, wx.ALL, 5)
        app_scroll_sizer.Add(row, 0, wx.EXPAND)

        reset_lock = self.make_button(app_scroll, "Reset Lock Screen Section", lambda evt: self._reset_appearance_section("lockscreen", app_scroll_sizer, app_scroll, app_config), "Reset Lock Screen")
        app_scroll_sizer.Add(reset_lock, 0, wx.CENTER | wx.TOP, 5)

        # Apply button
        app_scroll_sizer.Add(self.make_button(app_scroll, "Apply & Save Appearance", self.on_apply_appearance, "Apply Appearance"), 0, wx.ALL | wx.CENTER, 15)

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
        self.show_info("Lock settings saved.")
        self.lock_status.SetLabel("Lock settings saved.")
        self.api.speak("Lock settings saved.")

    def on_clear_lock(self, event):
        if not self.confirm_delete("lock screen and clear PIN/password"):
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

    def on_voice_change(self, event):
        if hasattr(self, 'voice_choice'):
            idx = self.voice_choice.GetSelection()
            setter = getattr(self.api.engine, "set_sapi_voice", None)
            if setter:
                setter(idx)
                self.api.speak("Voice changed.")

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
