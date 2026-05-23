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
from api import SystemAPI
from lockscreen import LockScreen, load_config as load_lock_config

class DesktopFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="PyOS Desktop", size=(800, 600))
        
        # Core OS path
        self.data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.os_kernel = kernel.VirtualOS()
        self.sound_manager = sounds.SoundManager(self.data_dir)
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
        
        # Play startup sound via theme
        self.api.play_sound("startup")

        ac = self.appearance_config
        self.panel = wx.Panel(self)
        self.panel.SetBackgroundColour(wx.Colour(ac.get("desktop_bg", "#000000")))
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Desktop Header
        self.header = wx.StaticText(self.panel, label=ac.get("desktop_header", "PyOS Desktop"))
        self.header.SetForegroundColour(wx.Colour(ac.get("desktop_header_color", "#FFFFFF")))
        self.header.SetFont(wx.Font(ac.get("desktop_header_font_size", 18), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.sizer.Add(self.header, 0, wx.ALL | wx.CENTER, 20)

        self.scrolled_window = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.scrolled_window.SetScrollRate(0, ac.get("desktop_scroll_rate", 20))
        self.scrolled_window.SetBackgroundColour(wx.Colour(ac.get("desktop_bg", "#000000")))
        self.app_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scrolled_window.SetSizer(self.app_sizer)
        self.sizer.Add(self.scrolled_window, 1, wx.EXPAND | wx.ALL, 10)

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
        self.last_activity = time.time()
        self.auto_lock_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_auto_lock_check, self.auto_lock_timer)
        self.auto_lock_timer.Start(30000)
        self.ctrl_hold_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_ctrl_hold, self.ctrl_hold_timer)
        self.Bind(wx.EVT_KEY_UP, self._on_key_up)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_ACTIVATE, self.on_activity)
        wx.CallAfter(self.check_lock)
        wx.CallAfter(self.greet)

    def on_key_down(self, event):
        self.on_activity()
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_F1:
            self.show_help()
        elif event.ControlDown() and keycode == ord('D'):
            self.show_docs()
        elif keycode == wx.WXK_CONTROL:
            if not self.ctrl_hold_timer.IsRunning():
                self.ctrl_hold_timer.Start(5000, wx.TIMER_ONE_SHOT)
        else:
            self.ctrl_hold_timer.Stop()
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

    def _on_key_up(self, event):
        if event.GetKeyCode() == wx.WXK_CONTROL:
            self.ctrl_hold_timer.Stop()
        event.Skip()

    def _on_ctrl_hold(self, event):
        self._show_ctrl_menu()

    def _show_ctrl_menu(self):
        menu = wx.Menu()
        menu.Append(5011, "Lock Screen")
        menu.AppendSeparator()
        menu.Append(5012, "Restart")
        menu.Append(5013, "Shutdown")
        self.Bind(wx.EVT_MENU, self._on_ctrl_menu_item)
        self.PopupMenu(menu)
        menu.Destroy()

    def _on_ctrl_menu_item(self, event):
        id_ = event.GetId()
        if id_ == 5011:
            config = load_lock_config(self.data_dir)
            if config.get("enabled"):
                dlg = LockScreen(self, self.data_dir)
                dlg.ShowModal()
            else:
                self.api.speak("No lock screen configured.")
        elif id_ == 5012:
            import sys, subprocess
            subprocess.Popen([sys.executable, __file__])
            self._allow_close = True
            self.Close()
            wx.CallAfter(wx.Exit)
        elif id_ == 5013:
            self._allow_close = True
            self.Close()
            wx.CallAfter(wx.Exit)

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
                self.show_lock_screen()

    def show_lock_screen(self):
        dlg = LockScreen(self, self.data_dir)
        dlg.ShowModal()
        if dlg.unlocked:
            self.last_activity = time.time()
        else:
            self.Close()

    def check_lock(self):
        config = load_lock_config(self.data_dir)
        if config.get("enabled"):
            dlg = LockScreen(self, self.data_dir)
            dlg.ShowModal()
            if not dlg.unlocked:
                self.Close()

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
            btn.SetFont(wx.Font(font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_MEDIUM))
            btn.SetBackgroundColour(btn_bg)
            btn.SetForegroundColour(btn_fg)
            
            btn.Bind(wx.EVT_BUTTON, lambda evt, a=app: self.on_launch_app(a))
            btn.Bind(wx.EVT_SET_FOCUS, lambda evt, a=app: self.on_item_focused(a))
            
            self.app_sizer.Add(btn, 0, wx.EXPAND | wx.ALL, ac.get("desktop_button_spacing", 5))
            self.app_buttons.append(btn)
        
        self.app_sizer.Layout()
        self.panel.Layout()

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

        btn.PopupMenu(menu)
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

if __name__ == "__main__":
    app = wx.App()
    desktop = DesktopFrame()
    desktop.Show()
    app.MainLoop()
