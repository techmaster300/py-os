import wx
import os
import importlib.util
import speech
import kernel
import sounds
import threading
import time
import traceback
import config_manager
import translation
import sys as _sys
from api import SystemAPI, BlindApp
from lockscreen import LockScreen, load_config as load_lock_config

class BootScreen(BlindApp, wx.Frame):
    def __init__(self, safe_mode=False):
        self.safe_mode = safe_mode
        self.recovery_mode = False
        style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX)
        wx.Frame.__init__(self, None, title="PyOS", size=(500, 300), style=style)
        self.Center()
        self.SetBackgroundColour(wx.Colour(0, 0, 0))
        panel = self.make_panel(self)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = self.vbox()

        logo = self.make_static(panel, "PyOS", font_size=48)
        logo.SetForegroundColour(wx.Colour(0, 180, 255))
        sizer.Add(logo, 0, wx.ALL | wx.CENTER, 30)

        hint = "Safe Mode" if safe_mode else "F1=Recovery  F2=Safe"
        self._sub = self.make_static(panel, hint, font_size=16)
        self._sub.SetForegroundColour(wx.Colour(180, 180, 180))
        sizer.Add(self._sub, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)
        self.Show()
        self.Layout()
        self.Refresh()
        wx.CallAfter(self._sub.SetFocus)

    def _beep(self, high=880, low=660):
        try:
            import winsound
            winsound.Beep(high, 150)
            winsound.Beep(low, 150)
        except Exception:
            pass

    def poll_boot_keys(self):
        import ctypes
        VK_F1 = 0x70
        VK_F2 = 0x71
        start = time.time()
        while time.time() - start < 10.0:
            if ctypes.windll.user32.GetAsyncKeyState(VK_F1) & 0x8000:
                self.recovery_mode = True
                self._sub.SetLabel("Recovery Mode")
                self._beep(660, 330)
                speech.engine.speak("Recovery Mode")
                return
            if ctypes.windll.user32.GetAsyncKeyState(VK_F2) & 0x8000:
                self.safe_mode = True
                self._sub.SetLabel("Safe Mode")
                self._beep(880, 660)
                speech.engine.speak("Safe Mode")
                return
            wx.Yield()
            time.sleep(0.05)
        if not self.safe_mode and not self.recovery_mode:
            speech.engine.speak("PyOS")

    def close_after(self, delay_ms=2000):
        wx.CallLater(delay_ms, self.Close)

class DesktopFrame(wx.Frame):
    def __init__(self, safe_mode=False, recovery_mode=False):
        super().__init__(None, title="PyOS Desktop", size=(800, 600))
        
        self.safe_mode = safe_mode
        self.recovery_mode = recovery_mode
        
        # Core OS path
        self.data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.os_kernel = kernel.VirtualOS()
        self.sound_manager = sounds.SoundManager(self.data_dir)
        if self.safe_mode or self.recovery_mode:
            self.sound_manager.current_theme = "Modern"
        self.api = SystemAPI(self, self.os_kernel, speech.engine, self.sound_manager)
        self.appearance_config = config_manager.load_appearance_config(self.data_dir)
        self.sys_config = config_manager.load_config(self.data_dir)
        lang = self.sys_config.get("language", "en")
        translation.set_language(lang)
        ac = self.appearance_config
        self.SetSize(ac.get("desktop_width", 800), ac.get("desktop_height", 600))
        
        # Start background services
        try:
            self.api.network.start()
        except Exception as e:
            print(f"Network service failed to start, proceeding anyway: {e}")
            
        self.apps = []
        self.app_buttons = []
        self.active_app = None
        self.open_apps = []
        self.notifications = []
        self._app_hotkeys = {}
        
        # Play startup sound via theme
        self.api.play_sound("startup")

        ac = self.appearance_config
        self.panel = wx.Panel(self)
        self.panel.SetName("Desktop Panel")
        self.panel.SetBackgroundColour(wx.Colour(ac.get("desktop_bg", "#000000")))
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Desktop Header
        title = ac.get("desktop_header", "PyOS Desktop")
        if self.recovery_mode:
            title += " (Recovery Mode)"
        elif self.safe_mode:
            title += " (Safe Mode)"
        self.header = wx.StaticText(self.panel, label=title)
        self.header.SetName("Desktop Header")
        self.header.SetFont(wx.Font(ac.get("desktop_header_font_size", 18), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        if self.recovery_mode:
            self.header.SetForegroundColour(wx.Colour(255, 100, 0))
        elif self.safe_mode:
            self.header.SetForegroundColour(wx.Colour(255, 180, 0))
        self.sizer.Add(self.header, 0, wx.ALL | wx.CENTER, 20)

        self.scrolled_window = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.scrolled_window.SetName("App List Scroll")
        self.scrolled_window.SetScrollRate(0, ac.get("desktop_scroll_rate", 20))
        self.scrolled_window.SetBackgroundColour(wx.Colour(ac.get("desktop_bg", "#000000")))
        self.app_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scrolled_window.SetSizer(self.app_sizer)
        self.sizer.Add(self.scrolled_window, 1, wx.EXPAND | wx.ALL, 10)

        self._wallpaper_bmp = None
        self._wallpaper_scaled = None
        if not self.safe_mode and not self.recovery_mode:
            self._load_wallpaper(ac.get("wallpaper_path", ""))
        self.panel.Bind(wx.EVT_PAINT, self._on_paint_desktop)
        self.Bind(wx.EVT_SIZE, self._on_frame_resize)

        self.panel.SetSizer(self.sizer)

        # Global Hotkeys
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

        # Accelerators for navigation shortcuts (reliable even when buttons have focus)
        ID_NAV_BACK = 2001
        ID_NAV_OVERVIEW = 2002
        ID_NAV_HOME = 2003
        ID_NAV_NOTIF = 2004
        accel = wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_LEFT, ID_NAV_BACK),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_RIGHT, ID_NAV_OVERVIEW),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_DOWN, ID_NAV_HOME),
            wx.AcceleratorEntry(wx.ACCEL_CTRL, wx.WXK_UP, ID_NAV_NOTIF),
        ])
        self.SetAcceleratorTable(accel)
        self.Bind(wx.EVT_MENU, self.nav_back, id=ID_NAV_BACK)
        self.Bind(wx.EVT_MENU, self.nav_overview, id=ID_NAV_OVERVIEW)
        self.Bind(wx.EVT_MENU, self.nav_home, id=ID_NAV_HOME)
        self.Bind(wx.EVT_MENU, self.nav_notifications, id=ID_NAV_NOTIF)

        self.load_plugins()
        self._load_hotkeys()
        self.last_activity = time.time()
        self.auto_lock_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_auto_lock_check, self.auto_lock_timer)
        self.auto_lock_timer.Start(30000)
        self.ctrl_hold_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_ctrl_hold, self.ctrl_hold_timer)
        self.lock_check_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._check_lock_keys, self.lock_check_timer)
        self.lock_check_timer.Start(300)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_activity)
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self._on_menu_highlight)
        self._menu_open = False
        wx.CallAfter(self.greet)

    def on_key_down(self, event):
        self.on_activity()
        keycode = event.GetKeyCode()
        if event.ControlDown():
            if keycode == wx.WXK_LEFT:
                self.nav_back(); return
            elif keycode == wx.WXK_RIGHT:
                self.nav_overview(); return
            elif keycode == wx.WXK_DOWN:
                self.nav_home(); return
            elif keycode == wx.WXK_UP:
                self.nav_notifications(); return
            elif keycode == ord('D'):
                self.show_docs(); return
            elif keycode != wx.WXK_CONTROL:
                event.Skip(); return
        hotkey_app = self._match_hotkey(event)
        if hotkey_app:
            self._launch_via_hotkey(hotkey_app)
            return
        if keycode == wx.WXK_F1:
            self.show_help()
        elif keycode == wx.WXK_CONTROL:
            if not self.ctrl_hold_timer.IsRunning():
                self.ctrl_hold_timer.Start(3000, wx.TIMER_ONE_SHOT)
        else:
            self.ctrl_hold_timer.Stop()
            event.Skip()

    def _on_menu_highlight(self, event):
        if self._menu_open:
            self.api.play_sound("nav")
        event.Skip()

    def show_help(self):
        if self.active_app:
            msg = f"Help for {self.active_app.name}: {self.active_app.help_text}"
        else:
            msg = translation._("desktop.help")
        self.api.speak(msg)

    def show_docs(self):
        if self.active_app:
            msg = f"Documentation for {self.active_app.name}: {self.active_app.docs}"
        else:
            msg = translation._("desktop.docs")
        self.api.speak(msg)

    def _on_ctrl_hold(self, event):
        if wx.GetKeyState(wx.WXK_CONTROL):
            self._show_power_dialog()

    def _show_power_dialog(self):
        self.api.play_sound("power_menu")
        menu = wx.Menu()
        menu.Append(5012, "Restart")
        menu.Append(5015, "Restart in Safe Mode")
        menu.Append(5013, "Shutdown")
        menu.AppendSeparator()
        menu.Append(5014, "Emergency Shutdown")
        self.Bind(wx.EVT_MENU, self._on_power_action)
        self._menu_open = True
        self.PopupMenu(menu)
        self._menu_open = False
        menu.Destroy()

    def _on_power_action(self, event):
        id_ = event.GetId()
        import subprocess as _subprocess
        if id_ == 5012:
            self.api.play_sound("shutdown")
            _subprocess.Popen([_sys.executable, __file__])
            self._allow_close = True
            self.Close()
            wx.CallAfter(wx.Exit)
        elif id_ == 5015:
            self.api.play_sound("shutdown")
            _subprocess.Popen([_sys.executable, __file__, "--safe"])
            self._allow_close = True
            self.Close()
            wx.CallAfter(wx.Exit)
        elif id_ == 5013:
            self.api.play_sound("shutdown")
            self._allow_close = True
            self.Close()
            wx.CallAfter(wx.Exit)
        elif id_ == 5014:
            self._start_emergency_shutdown()

    def _start_emergency_shutdown(self):
        self.api.play_sound("alert")
        countdown = [3]
        timer = wx.Timer(self)
        dlg = wx.Dialog(self, title="Emergency Shutdown", size=(300, 120))
        dlg.SetName("Emergency Shutdown Dialog")
        dlg.SetBackgroundColour(wx.Colour(30, 0, 0))
        panel = wx.Panel(dlg)
        panel.SetName("Emergency Shutdown Panel")
        panel.SetBackgroundColour(wx.Colour(30, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        msg = wx.StaticText(panel, label="Shutting down in 3...")
        msg.SetName("Shutdown Countdown")
        msg.SetForegroundColour(wx.Colour(255, 100, 100))
        msg.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(msg, 1, wx.ALL | wx.CENTER, 20)

        hint = wx.StaticText(panel, label="Press Esc to cancel")
        hint.SetName("Cancel Hint")
        hint.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(hint, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)
        dlg.CenterOnParent()

        def on_tick(evt):
            countdown[0] -= 1
            if countdown[0] <= 0:
                timer.Stop()
                dlg.Close()
                import os as _os
                _os._exit(0)
            else:
                msg.SetLabel(f"Shutting down in {countdown[0]}...")
                timer.Start(1000, wx.TIMER_ONE_SHOT)

        def on_key(evt):
            if evt.GetKeyCode() == wx.WXK_ESCAPE:
                timer.Stop()
                dlg.Close()
            evt.Skip()

        self.Bind(wx.EVT_TIMER, on_tick, timer)
        dlg.Bind(wx.EVT_CHAR_HOOK, on_key)
        timer.Start(1000, wx.TIMER_ONE_SHOT)
        dlg.ShowModal()
        dlg.Destroy()

    def _on_close(self, event):
        if not getattr(self, '_allow_close', False):
            event.Veto()

    def on_activity(self, event=None):
        self.last_activity = time.time()
        if event:
            event.Skip()

    def on_auto_lock_check(self, event):
        if self.active_app:
            return
        config = load_lock_config(self.data_dir)
        minutes = config.get("auto_lock_minutes", 0)
        if minutes > 0 and config.get("enabled"):
            elapsed = (time.time() - self.last_activity) / 60
            if elapsed >= minutes:
                self.lock_system()

    def _check_lock_keys(self, event):
        import ctypes
        VK_MENU = 0x12
        VK_SHIFT = 0x10
        alt_down = (ctypes.windll.user32.GetAsyncKeyState(VK_MENU) >> 15) & 1
        shift_down = (ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) >> 15) & 1
        if alt_down and shift_down:
            config = load_lock_config(self.data_dir)
            if config.get("hash"):
                self.lock_check_timer.Stop()
                self.lock_system()

    def _load_hotkeys(self):
        self._app_hotkeys = {}
        raw = self.sys_config.get("app_hotkeys", {})
        key_map = {v: k for k, v in raw.items()}
        for app in self.apps:
            if hasattr(app, 'hotkey') and app.hotkey:
                self._app_hotkeys[app.hotkey] = app
        for combo, app_name in key_map.items():
            for app in self.apps:
                if app.name == app_name:
                    self._app_hotkeys[combo] = app
                    break

    def _launch_via_hotkey(self, app):
        try:
            self.active_app = app
            self.open_apps.append(app)
            self.api.play_sound("launch")
            self.api.speak(translation._("desktop.launching", name=app.name))
            app.run()
        except Exception as e:
            self.api.speak(f"Failed to launch {app.name}: {e}")

    def _match_hotkey(self, event):
        keycode = event.GetKeyCode()
        parts = []
        if event.ControlDown():
            parts.append("Ctrl")
        if event.AltDown():
            parts.append("Alt")
        if event.ShiftDown():
            parts.append("Shift")
        key_name = None
        if keycode == ord('A') <= keycode <= ord('Z'):
            key_name = chr(keycode)
        elif keycode >= ord('0') and keycode <= ord('9'):
            key_name = chr(keycode)
        elif keycode == wx.WXK_F1:
            key_name = "F1"
        elif keycode == wx.WXK_F2:
            key_name = "F2"
        elif keycode == wx.WXK_F3:
            key_name = "F3"
        elif keycode == wx.WXK_F4:
            key_name = "F4"
        elif keycode == wx.WXK_F5:
            key_name = "F5"
        elif keycode == wx.WXK_F6:
            key_name = "F6"
        elif keycode == wx.WXK_F7:
            key_name = "F7"
        elif keycode == wx.WXK_F8:
            key_name = "F8"
        elif keycode == wx.WXK_F9:
            key_name = "F9"
        elif keycode == wx.WXK_F10:
            key_name = "F10"
        elif keycode == wx.WXK_F11:
            key_name = "F11"
        elif keycode == wx.WXK_F12:
            key_name = "F12"
        if not key_name:
            return None
        if not parts:
            return None
        combo = "+".join(parts) + "+" + key_name
        return self._app_hotkeys.get(combo)

    def lock_system(self):
        self.api.play_sound("logoff")
        self.show_lock_screen()
        if not self.lock_check_timer.IsRunning():
            self.lock_check_timer.Start(300)

    def show_lock_screen(self):
        dlg = LockScreen(self, self.data_dir, sounds=self.sound_manager)
        dlg.ShowModal()
        if dlg.unlocked:
            self.last_activity = time.time()
        else:
            self.Close()
        dlg.Destroy()

    def _load_wallpaper(self, path):
        self._wallpaper_bmp = None
        self._wallpaper_scaled = None
        if path and os.path.exists(path):
            try:
                bmp = wx.Bitmap(path, wx.BITMAP_TYPE_ANY)
                if bmp.IsOk():
                    self._wallpaper_bmp = bmp
                    self._wallpaper_scaled = None
            except Exception:
                pass

    def _on_frame_resize(self, event):
        self._wallpaper_scaled = None
        event.Skip()

    def _on_paint_desktop(self, event):
        dc = wx.PaintDC(self.panel)
        bmp = self._wallpaper_bmp
        if not bmp:
            event.Skip()
            return
        pw, ph = self.panel.GetSize()
        if pw <= 0 or ph <= 0:
            event.Skip()
            return
        if self._wallpaper_scaled is None:
            style = self.appearance_config.get("wallpaper_style", "stretch")
            bw, bh = bmp.GetSize()
            if bw == 0 or bh == 0:
                event.Skip(); return
            if style == "stretch":
                img = bmp.ConvertToImage().Scale(pw, ph, wx.IMAGE_QUALITY_HIGH)
                self._wallpaper_scaled = {"bmp": wx.Bitmap(img), "x": 0, "y": 0, "tile": False}
            elif style == "fit":
                scale = min(pw / bw, ph / bh)
                nw, nh = int(bw * scale), int(bh * scale)
                img = bmp.ConvertToImage().Scale(nw, nh, wx.IMAGE_QUALITY_HIGH)
                self._wallpaper_scaled = {"bmp": wx.Bitmap(img), "x": (pw - nw) // 2, "y": (ph - nh) // 2, "tile": False}
            elif style == "center":
                self._wallpaper_scaled = {"bmp": bmp, "x": (pw - bw) // 2, "y": (ph - bh) // 2, "tile": False}
            elif style == "tile":
                self._wallpaper_scaled = {"bmp": bmp, "x": 0, "y": 0, "tile": True}
        if self._wallpaper_scaled["tile"]:
            tb = self._wallpaper_scaled["bmp"]
            tw, th = tb.GetSize()
            for x in range(0, pw, tw):
                for y in range(0, ph, th):
                    dc.DrawBitmap(tb, x, y)
        else:
            dc.DrawBitmap(self._wallpaper_scaled["bmp"], self._wallpaper_scaled["x"], self._wallpaper_scaled["y"])

    def set_wallpaper(self, path):
        ac = self.appearance_config
        ac["wallpaper_path"] = path
        config_manager.save_appearance_config(self.data_dir, ac)
        self._load_wallpaper(path)
        self.panel.Refresh()

    def greet(self):
        msg = getattr(self, 'appearance_config', {}).get("desktop_greeting", translation._("desktop.greeting"))
        self.api.speak(msg)
        if self.app_buttons:
            self.app_buttons[0].SetFocus()

    def load_plugins(self):
        apps_dir = os.path.join(os.getcwd(), "apps")
        if not os.path.exists(apps_dir):
            os.makedirs(apps_dir)
        
        self.apps = []
        if self.safe_mode or self.recovery_mode:
            safe_only = {"system_apps.py", "terminal.py", "help_app.py", "calculator.py", "text_editor.py", "clock_app.py"}
            for fname in os.listdir(apps_dir):
                if fname in safe_only:
                    self.load_app_from_file(os.path.join(apps_dir, fname))
        else:
            for filename in os.listdir(apps_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    self.load_app_from_file(os.path.join(apps_dir, filename))

        self.refresh_app_list()

    def load_app_from_file(self, path):
        try:
            module_name = os.path.basename(path)[:-3]
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            from api import BlindApp
            for attr in dir(module):
                cls = getattr(module, attr)
                if isinstance(cls, type) and issubclass(cls, BlindApp) and cls is not BlindApp:
                    try:
                        app_instance = cls(self.api)
                        self.apps.append(app_instance)
                        print(f"Loaded app: {app_instance.name}")
                    except Exception as e:
                        print(f"Error instantiating {cls.__name__} from {path}: {e}")
        except Exception as e:
            print(f"Failed to load module at {path}: {e}")

    def refresh_app_list(self):
        self.app_sizer.Clear(True)
        self.app_buttons = []

        ac = getattr(self, 'appearance_config', {})
        btn_bg = wx.Colour(ac.get("desktop_button_bg", "#282828"))
        btn_fg = wx.Colour(ac.get("desktop_button_fg", "#FFFFFF"))
        font_size = ac.get("desktop_button_font_size", 16)

        hidden = self.sys_config.get("hidden_apps", [])

        # Define priority items to move to the end
        priority_end = ["Text Editor", "Terminal"]
        
        # Filter out hidden apps, then split into normal and those to move to end
        visible_apps = [a for a in self.apps if a.name not in hidden]
        normal_apps = [a for a in visible_apps if a.name not in priority_end]
        ordered_end = [a for p in priority_end for a in visible_apps if a.name == p]

        self.apps = normal_apps + ordered_end

        for app in self.apps:
            btn = wx.Button(self.scrolled_window, label=app.name)
            btn.SetName(app.name)
            btn.SetFont(wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_MEDIUM))
            btn.SetBackgroundColour(btn_bg)
            btn.SetForegroundColour(btn_fg)
            
            btn.Bind(wx.EVT_BUTTON, lambda evt, a=app: self.on_launch_app(a))
            btn.Bind(wx.EVT_SET_FOCUS, lambda evt, a=app: self.on_item_focused(a))
            
            self.app_sizer.Add(btn, 0, wx.EXPAND | wx.ALL, ac.get("desktop_button_spacing", 5))
            self.app_buttons.append(btn)
        
        self.app_sizer.Layout()
        self.panel.Layout()
        self._load_hotkeys()

    def on_item_focused(self, app):
        try:
            if self.IsActive():
                self.api.play_sound("nav")
                self.api.speak(f"{app.name}: {app.description}")
        except Exception as e:
            print(f"Error in focus speech: {e}")

    def nav_back(self):
        if self.active_app and self.active_app.frame:
            self.active_app.close_app()
            self.active_app = None
            if self.app_buttons:
                self.app_buttons[0].SetFocus()
            self.api.speak(translation._("nav.desktop"))
        else:
            self.api.speak(translation._("desktop.already_on_desktop"))

    def push_notification(self, title, message, level='info'):
        self.notifications.insert(0, {"title": title, "message": message, "level": level})
        if len(self.notifications) > 20:
            self.notifications.pop()

    def nav_overview(self):
        if not self.open_apps:
            self.api.speak(translation._("desktop.no_open_apps"))
            return
        names = [a.name for a in self.open_apps]
        dlg = wx.SingleChoiceDialog(self, translation._("desktop.switch_hint"), translation._("desktop.open_apps_overview"), names)
        dlg.SetName("Open Apps Overview")
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetSelection()
            app = self.open_apps[sel]
            if app.frame:
                app.frame.Raise()
                app.frame.SetFocus()
            self.api.speak(app.name)
        dlg.Destroy()

    def nav_notifications(self):
        if not self.notifications:
            self.api.speak(translation._("desktop.no_notifications"))
            return
        items = [f"[{n['level']}] {n['title']}: {n['message']}" for n in self.notifications]
        dlg = wx.SingleChoiceDialog(self, translation._("desktop.notification_hint"), translation._("desktop.notification_shade"), items)
        dlg.SetName("Notifications List")
        dlg.SetBackgroundColour(wx.Colour(0, 0, 0))
        if dlg.ShowModal() == wx.ID_OK:
            sel = dlg.GetSelection()
            dismissed = self.notifications.pop(sel)
            self.api.speak(translation._("desktop.dismissed", title=dismissed['title']))
            dlg.Destroy()
            if self.notifications:
                self.nav_notifications()
            return
        dlg.Destroy()

    def nav_home(self):
        if self.active_app:
            try:
                if self.active_app.frame:
                    self.active_app.close_app()
            except Exception:
                pass
            self.active_app = None
        if self.app_buttons:
            self.app_buttons[0].SetFocus()
        self.api.speak(translation._("nav.home"))

    def on_launch_app(self, app):
        if wx.GetKeyState(wx.WXK_CONTROL):
            focused = wx.Window.FindFocus()
            self.show_app_context_menu(focused if focused else self, app)
            return
        try:
            self.active_app = app
            self.open_apps.append(app)
            self.api.play_sound("launch")
            self.api.speak(translation._("desktop.launching", name=app.name))
            app.run()
        except Exception as e:
            msg = f"Failed to launch {app.name}: {e}"
            self.api.speak(msg)

    def on_app_closed(self, app_instance):
        self.active_app = None
        if app_instance in self.open_apps:
            self.open_apps.remove(app_instance)
        try:
            self.api.speak(translation._("desktop.closed", name=app_instance.name), interrupt=False)
        except Exception: pass
        wx.CallAfter(self._return_focus, app_instance.name)

    def _return_focus(self, app_name):
        # Update app_buttons list to remove any buttons that were destroyed
        self.app_buttons = [btn for btn in self.app_buttons if btn and btn.IsShownOnScreen()]
        
        if self.app_buttons:
            for btn in self.app_buttons:
                if btn.GetLabel() == app_name:
                    btn.SetFocus()
                    break
            else:
                self.app_buttons[0].SetFocus()

    def show_app_context_menu(self, btn, app):
        self.api.play_sound("context_menu")
        menu = wx.Menu()
        hidden = self.sys_config.get("hidden_apps", [])
        if app.name in hidden:
            pin_item = menu.Append(wx.ID_ANY, "&Pin to Desktop")
            self.Bind(wx.EVT_MENU, lambda evt, a=app: self.on_pin_app(a), pin_item)
        else:
            unpin_item = menu.Append(wx.ID_ANY, "&Unpin from Desktop")
            self.Bind(wx.EVT_MENU, lambda evt, a=app: self.on_unpin_app(a), unpin_item)

        uninstall_item = menu.Append(wx.ID_ANY, "&Uninstall")
        self.Bind(wx.EVT_MENU, lambda evt, a=app: self.on_uninstall_app(a), uninstall_item)

        menu.AppendSeparator()
        hotkey_item = menu.Append(wx.ID_ANY, "&Set Hotkey...")
        self.Bind(wx.EVT_MENU, lambda evt, a=app: self.on_set_hotkey(a), hotkey_item)

        self._menu_open = True
        btn.PopupMenu(menu)
        self._menu_open = False
        menu.Destroy()

    def on_unpin_app(self, app):
        hidden = self.sys_config.get("hidden_apps", [])
        if app.name not in hidden:
            hidden.append(app.name)
        self.sys_config["hidden_apps"] = hidden
        config_manager.save_config(self.data_dir, self.sys_config)
        self.api.speak(f"{app.name} unpinned from desktop.")
        self.refresh_app_list()

    def on_pin_app(self, app):
        hidden = self.sys_config.get("hidden_apps", [])
        if app.name in hidden:
            hidden.remove(app.name)
        self.sys_config["hidden_apps"] = hidden
        config_manager.save_config(self.data_dir, self.sys_config)
        self.api.speak(f"{app.name} pinned to desktop.")
        self.refresh_app_list()

    def on_uninstall_app(self, app):
        result = wx.MessageBox(f"Are you sure you want to uninstall {app.name}?", "Confirm Uninstall",
                               wx.YES_NO | wx.ICON_QUESTION, self)
        if result != wx.YES:
            self.api.speak("Uninstall cancelled.")
            return
        apps_dir = os.path.join(os.getcwd(), "apps")
        for fname in os.listdir(apps_dir):
            if fname.endswith(".py") and fname != "__init__.py":
                spec = importlib.util.spec_from_file_location(fname[:-3], os.path.join(apps_dir, fname))
                if spec and spec.loader:
                    try:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        from api import BlindApp
                        for attr in dir(module):
                            cls = getattr(module, attr)
                            if isinstance(cls, type) and issubclass(cls, BlindApp) and cls is not BlindApp:
                                if getattr(cls(self.api), 'name', None) == app.name:
                                    fpath = os.path.join(apps_dir, fname)
                                    os.remove(fpath)
                                    self.api.speak(f"{app.name} uninstalled.")
                                    # Remove from hidden list if present
                                    hidden = self.sys_config.get("hidden_apps", [])
                                    if app.name in hidden:
                                        hidden.remove(app.name)
                                        self.sys_config["hidden_apps"] = hidden
                                        config_manager.save_config(self.data_dir, self.sys_config)
                                    self.load_plugins()
                                    return
                    except Exception:
                        continue
        self.api.speak("Could not find app file to uninstall.")

    def on_set_hotkey(self, app):
        current = ""
        for combo, a in self._app_hotkeys.items():
            if a is app:
                current = combo
                break
        dlg = wx.TextEntryDialog(self, f"Enter hotkey for {app.name}\n(e.g. Ctrl+T, Ctrl+Shift+F5)\nLeave empty to clear.", "Set Hotkey", current)
        dlg.SetName("Hotkey Input")
        if dlg.ShowModal() == wx.ID_OK:
            combo = dlg.GetValue().strip()
            raw = self.sys_config.get("app_hotkeys", {})
            # Remove old entries for this app
            for k, v in list(raw.items()):
                if v == app.name:
                    del raw[k]
            for k, v in list(self._app_hotkeys.items()):
                if v is app:
                    del self._app_hotkeys[k]
            if combo:
                raw[combo] = app.name
                self._app_hotkeys[combo] = app
                self.api.speak(f"Hotkey {combo} set for {app.name}")
            else:
                self.api.speak(f"Hotkey cleared for {app.name}")
            self.sys_config["app_hotkeys"] = raw
            config_manager.save_config(self.data_dir, self.sys_config)
        dlg.Destroy()

class RecoveryMenu(wx.Frame):
    def __init__(self, data_dir):
        super().__init__(None, title="PyOS Recovery", size=(600, 400))
        self.data_dir = data_dir
        self.Center()
        self.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)

        heading = wx.StaticText(self.panel, label="PyOS Recovery")
        heading.SetFont(wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        heading.SetForegroundColour(wx.Colour(255, 180, 0))
        sizer.Add(heading, 0, wx.ALL | wx.CENTER, 20)

        sub = wx.StaticText(self.panel, label="Use UP/DOWN to navigate, ENTER to select")
        sub.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sub.SetForegroundColour(wx.Colour(140, 140, 140))
        sizer.Add(sub, 0, wx.ALL | wx.CENTER, 5)

        self.items = [
            ("Reboot system now", self._reboot),
            ("Apply update from ADB", self._adb_placeholder),
            ("Wipe data/factory reset", self._wipe_data),
            ("Wipe cache partition", self._wipe_cache),
            ("Launch Safe Mode", self._safe_mode),
        ]
        self._sel = 0
        self._labels = []
        for i, (text, _) in enumerate(self.items):
            st = wx.StaticText(self.panel, label=f"  [{i+1}] {text}")
            st.SetFont(wx.Font(14, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            st.SetForegroundColour(wx.Colour(180, 180, 180))
            self._labels.append(st)
            sizer.Add(st, 0, wx.ALL | wx.LEFT, 5)

        self.panel.SetSizer(sizer)
        self._update_selection()
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        wx.CallAfter(speech.engine.speak, "PyOS Recovery. Use up down to navigate, enter to select.")

    def _on_close(self, event):
        if not getattr(self, '_allow_close', False):
            event.Veto()

    def _update_selection(self):
        for i, st in enumerate(self._labels):
            if i == self._sel:
                st.SetForegroundColour(wx.Colour(0, 180, 255))
                st.SetLabel(f"> [{i+1}] {self.items[i][0]}")
            else:
                st.SetForegroundColour(wx.Colour(180, 180, 180))
                st.SetLabel(f"  [{i+1}] {self.items[i][0]}")

    def _on_key(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_UP:
            self._sel = (self._sel - 1) % len(self.items)
            self._update_selection()
            speech.engine.speak(self.items[self._sel][0])
        elif key == wx.WXK_DOWN:
            self._sel = (self._sel + 1) % len(self.items)
            self._update_selection()
            speech.engine.speak(self.items[self._sel][0])
        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            speech.engine.speak(self.items[self._sel][0])
            self._execute(self._sel)
        elif ord('1') <= key <= ord('9'):
            idx = key - ord('1')
            if idx < len(self.items):
                speech.engine.speak(self.items[idx][0])
                self._execute(idx)
        else:
            event.Skip()

    def _execute(self, idx):
        self.items[idx][1]()

    def _reboot(self):
        speech.engine.speak("Rebooting")
        self._allow_close = True
        self.Close()
        wx.CallAfter(self._launch_normal)

    def _launch_normal(self):
        import subprocess
        subprocess.Popen([_sys.executable, __file__])
        wx.CallAfter(wx.Exit)

    def _adb_placeholder(self):
        speech.engine.speak("Apply update from ADB is not yet implemented")

    def _wipe_data(self):
        config_manager.reset_all_configs(self.data_dir)
        speech.engine.speak("Factory reset complete")
        self._show_done("Factory reset complete")

    def _wipe_cache(self):
        apath = config_manager.get_appearance_path(self.data_dir)
        if os.path.exists(apath):
            os.remove(apath)
        speech.engine.speak("Cache wiped")
        self._show_done("Cache wiped")

    def _safe_mode(self):
        speech.engine.speak("Launching safe mode")
        self._allow_close = True
        self.Close()
        wx.CallAfter(self._launch_safe)

    def _launch_safe(self):
        import subprocess
        subprocess.Popen([_sys.executable, __file__, "--safe"])
        wx.CallAfter(wx.Exit)

    def _show_done(self, msg):
        for st in self._labels:
            st.Hide()
        done = wx.StaticText(self.panel, label=msg + "\n\nPress ENTER to reboot")
        done.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        done.SetForegroundColour(wx.Colour(0, 255, 0))
        self.panel.GetSizer().Add(done, 0, wx.ALL | wx.CENTER, 30)
        self.panel.Layout()
        self._done_action = lambda: self._reboot()
        self.Bind(wx.EVT_CHAR_HOOK, lambda e: self._reboot() if e.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) else None)

if __name__ == "__main__":
    _safe = "--safe" in _sys.argv
    _recovery = "--recovery" in _sys.argv
    app = wx.App()
    boot = BootScreen(safe_mode=_safe or _recovery)
    if not _safe and not _recovery:
        boot.poll_boot_keys()
    if boot.recovery_mode:
        boot.Destroy()
        data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        rec = RecoveryMenu(data_dir)
        rec.Show()
    else:
        desktop = DesktopFrame(safe_mode=boot.safe_mode, recovery_mode=boot.recovery_mode)
        desktop.Show()
        boot.close_after(1000)
    app.MainLoop()
