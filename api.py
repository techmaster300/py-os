import wx
import speech
import os
import json
import threading
import subprocess
import importlib
from network_service import NetworkService
from translation import _


class BlindApp:
    """Base class for all PyOS applications."""

    def __init__(self, api):
        self.api = api
        self.name = "Abstract App"
        self.description = "Base application class"
        self.help_text = "No help available for this app."
        self.docs = "No documentation available."
        self.frame = None
        self._accel_entries = []
        self._tick_interval = 0
        self._tick_timer = None
        self._timers = []
        self._menu_bar = None
        self._status_label = None
        self._dpi_scale = None

    # ── Error resilience ──────────────────────────────────────────────────

    def _safe_call(self, func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"[{self.name}] Error in {getattr(func, '__name__', 'call')}: {e}")
            return None

    def run(self):
        pass

    def on_focus(self):
        pass

    def on_blur(self):
        pass

    def on_tick(self):
        pass

    def on_open(self, filepath=None):
        pass

    # ── Dialog helpers (centered + resilient) ─────────────────────────────

    def _center_dialog(self, dlg):
        if self.frame:
            dlg.CentreOnParent()
        else:
            dlg.CentreOnScreen()

    def confirm(self, message, title="Confirm"):
        try:
            dlg = wx.MessageDialog(self.frame or None, message, title, wx.YES_NO | wx.ICON_QUESTION)
            self._center_dialog(dlg)
            result = dlg.ShowModal() == wx.ID_YES
            dlg.Destroy()
            return result
        except Exception:
            return False

    def alert(self, message, title="Alert"):
        try:
            dlg = wx.MessageDialog(self.frame or None, message, title, wx.OK | wx.ICON_INFORMATION)
            self._center_dialog(dlg)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception:
            self.api.speak(f"{title}: {message}")

    def prompt(self, message, default="", title="Input"):
        try:
            dlg = wx.TextEntryDialog(self.frame or None, message, title, default)
            self._center_dialog(dlg)
            if dlg.ShowModal() == wx.ID_OK:
                result = dlg.GetValue()
                dlg.Destroy()
                return result
            dlg.Destroy()
            return None
        except Exception:
            return None

    def choice(self, message, choices, title="Select"):
        if not choices:
            return None
        try:
            dlg = wx.SingleChoiceDialog(self.frame or None, message, title, choices)
            self._center_dialog(dlg)
            if dlg.ShowModal() == wx.ID_OK:
                result = dlg.GetStringSelection()
                dlg.Destroy()
                return result
            dlg.Destroy()
            return None
        except Exception:
            return None

    def notify(self, title, message, level='info'):
        self.api.notify(title, message, level)

    # ── Accelerator table ─────────────────────────────────────────────────

    def bind_accelerator(self, flags, key_code, command_id, handler, description=""):
        self._accel_entries.append((flags, key_code, command_id, handler, description))

    def _apply_accelerators(self):
        if not self._accel_entries or not self.frame:
            return
        entries = []
        for flags, key, cmd_id, handler, desc in self._accel_entries:
            entries.append((flags, key, cmd_id))
            self.frame.Bind(wx.EVT_MENU, handler, id=cmd_id)
        if entries:
            self.frame.SetAcceleratorTable(wx.AcceleratorTable(entries))

    # ── Simple shortcut registration ──────────────────────────────────────

    _next_key_id = 3000

    def key(self, combo, handler):
        combo = combo.replace("Ctrl+", "ACCEL_CTRL+").replace("Alt+", "ACCEL_ALT+").replace("Shift+", "ACCEL_SHIFT+")
        parts = combo.rsplit("+", 1)
        flags_str = parts[0] if len(parts) == 2 else "ACCEL_NORMAL"
        key_str = parts[-1]
        flags_map = {"ACCEL_CTRL": wx.ACCEL_CTRL, "ACCEL_ALT": wx.ACCEL_ALT, "ACCEL_SHIFT": wx.ACCEL_SHIFT, "ACCEL_NORMAL": wx.ACCEL_NORMAL}
        flags = 0
        for f in flags_str.split("+"):
            flags |= flags_map.get(f.strip(), wx.ACCEL_NORMAL)
        if key_str.startswith("WXK_"):
            key_code = getattr(wx, key_str, ord(key_str[0]))
        elif len(key_str) == 1:
            key_code = ord(key_str.upper())
        else:
            key_code = getattr(wx, f"WXK_{key_str.upper()}", ord(key_str[0]))
        cmd_id = BlindApp._next_key_id
        BlindApp._next_key_id += 1
        self.bind_accelerator(flags, key_code, cmd_id, handler)
        return cmd_id

    # ── Per-app config ────────────────────────────────────────────────────

    def _app_config_path(self):
        return self.api.get_data_path(f"appcfg_{self.__class__.__name__}.json")

    def load_app_config(self):
        try:
            path = self._app_config_path()
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_app_config(self, cfg):
        try:
            with open(self._app_config_path(), "w") as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            pass

    # ── Dirty tracking / confirm close ────────────────────────────────────

    confirm_close = False

    def set_dirty(self, state=True):
        self._dirty = state

    def is_dirty(self):
        return getattr(self, '_dirty', False)

    def on_close(self, event=None):
        if self.confirm_close and self.is_dirty():
            if not self.confirm(_("app.unsaved_changes", "You have unsaved changes. Close anyway?"), _("common.confirm")):
                if event:
                    event.Veto()
                return
        if self._tick_timer:
            self._tick_timer.Stop()
            self._tick_timer = None
        self.stop_timers()
        self._save_position()
        if self.frame:
            self.frame.Destroy()
            self.frame = None
        self.play_sound("close")
        self._safe_call(self.api.desktop.on_app_closed, self)

    def close_app(self):
        self._allow_close = True
        if self.frame:
            self.frame.Close()

    # ── Clipboard helpers ─────────────────────────────────────────────────

    @staticmethod
    def copy(text):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(str(text)))
            wx.TheClipboard.Close()

    @staticmethod
    def paste():
        if wx.TheClipboard.Open():
            data = wx.TextDataObject()
            if wx.TheClipboard.GetData(data):
                wx.TheClipboard.Close()
                return data.GetText()
            wx.TheClipboard.Close()
        return ""

    # ── Busy indicator ────────────────────────────────────────────────────

    def show_busy(self, message=""):
        if self.frame:
            self.frame.SetCursor(wx.Cursor(wx.CURSOR_WAIT))
        if message:
            self.set_status(message)

    def hide_busy(self):
        if self.frame:
            self.frame.SetCursor(wx.Cursor(wx.CURSOR_DEFAULT))
        self._clear_status()

    # ── Control factory (auto-SetName) ─────────────────────────────────────

    def make_button(self, parent, label, handler=None, name=""):
        btn = wx.Button(parent, label=label)
        btn.SetName(name or label)
        if handler:
            btn.Bind(wx.EVT_BUTTON, handler)
        return btn

    def make_textctrl(self, parent, value="", name="", style=0, size=None):
        kwargs = dict(value=value, style=style)
        if size is not None:
            kwargs["size"] = size
        ctrl = wx.TextCtrl(parent, **kwargs)
        if name:
            ctrl.SetName(name)
        return ctrl

    def make_listbox(self, parent, choices=None, name=""):
        lb = wx.ListBox(parent, choices=choices or [])
        if name:
            lb.SetName(name)
        return lb

    def make_choice(self, parent, choices, name=""):
        c = wx.Choice(parent, choices=choices)
        if name:
            c.SetName(name)
        return c

    def make_listctrl(self, parent, name="", style=wx.LC_REPORT):
        ctrl = wx.ListCtrl(parent, style=style)
        if name:
            ctrl.SetName(name)
        return ctrl

    def make_static(self, parent, label, name="", size=None):
        kwargs = dict(label=label)
        if size is not None:
            kwargs["size"] = size
        st = wx.StaticText(parent, **kwargs)
        if name:
            st.SetName(name)
        return st

    def make_panel(self, parent, name=""):
        p = wx.Panel(parent)
        p.SetBackgroundColour(wx.Colour(20, 20, 20))
        if name:
            p.SetName(name)
        return p

    def make_slider(self, parent, value=50, min_v=0, max_v=100, name="", size=None):
        kwargs = dict(value=value, minValue=min_v, maxValue=max_v)
        if size is not None:
            kwargs["size"] = size
        s = wx.Slider(parent, **kwargs)
        if name:
            s.SetName(name)
        return s

    def make_checkbox(self, parent, label, handler=None, name=""):
        cb = wx.CheckBox(parent, label=label)
        cb.SetName(name or label)
        if handler:
            cb.Bind(wx.EVT_CHECKBOX, handler)
        return cb

    def make_spinctrl(self, parent, value=0, min_v=0, max_v=100, name="", size=None):
        kwargs = dict(value=str(value), min=min_v, max=max_v)
        if size is not None:
            kwargs["size"] = size
        sc = wx.SpinCtrl(parent, **kwargs)
        if name:
            sc.SetName(name)
        return sc

    def add_separator(self, sizer, border=5, parent=None):
        p = parent or self.frame
        if not p:
            return
        sep = wx.StaticLine(p, style=wx.LI_HORIZONTAL)
        sizer.Add(sep, 0, wx.EXPAND | wx.ALL, border)

    def is_dev(self):
        try:
            return self.api.desktop.sys_config.get("developer_mode", False)
        except Exception:
            return False

    def make_dev_setting(self, parent, label, name=""):
        st = wx.StaticText(parent, label=label)
        st.SetForegroundColour(wx.Colour(140, 140, 140))
        if name:
            st.SetName(name)
        return st

    # ── Sizer shortcuts ───────────────────────────────────────────────────

    @staticmethod
    def vbox():
        return wx.BoxSizer(wx.VERTICAL)

    @staticmethod
    def hbox():
        return wx.BoxSizer(wx.HORIZONTAL)

    @staticmethod
    def add_spacer(sizer, size=10):
        sizer.AddSpacer(size)

    @staticmethod
    def add_stretch(sizer, proportion=1):
        sizer.AddStretchSpacer(proportion)

    # ── Async helper ──────────────────────────────────────────────────────

    def run_async(self, func, callback=None, daemon=True):
        t = threading.Thread(target=self._async_wrapper, args=(func, callback), daemon=daemon)
        t.start()
        return t

    def _async_wrapper(self, func, callback):
        try:
            result = func()
            if callback:
                wx.CallAfter(callback, result)
        except Exception as e:
            print(f"[{self.name}] Async error: {e}")
            wx.CallAfter(self.api.speak, f"Error: {e}")

    # ── Convenience dialogs ───────────────────────────────────────────────

    def show_info(self, message, title=""):
        self.alert(message, title or self.name)

    def show_error(self, message, title=""):
        try:
            dlg = wx.MessageDialog(self.frame or None, message, title or _("common.error"), wx.OK | wx.ICON_ERROR)
            self._center_dialog(dlg)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception:
            self.api.speak(f"Error: {message}")

    def confirm_delete(self, name, title=""):
        msg = f"Delete '{name}'?" if name else "Delete this item?"
        return self.confirm(msg, title or _("common.confirm"))

    # ── Utility helpers ───────────────────────────────────────────────────

    @staticmethod
    def open_url(url):
        import webbrowser
        webbrowser.open(url)

    def help_topic(self):
        return self.help_text

    # ── Menu builder ──────────────────────────────────────────────────────

    def add_menu_bar(self):
        self._menu_bar = wx.MenuBar()
        if self.frame:
            self.frame.SetMenuBar(self._menu_bar)
        return self._menu_bar

    def add_menu(self, label):
        if not self._menu_bar:
            self.add_menu_bar()
        menu = wx.Menu()
        self._menu_bar.Append(menu, label)
        return menu

    def add_menu_item(self, menu, label, handler, shortcut=""):
        item = menu.Append(wx.ID_ANY, f"{label}\t{shortcut}" if shortcut else label)
        if self.frame:
            self.frame.Bind(wx.EVT_MENU, handler, item)
        return item

    # ── Status bar ────────────────────────────────────────────────────────

    def create_status_bar(self):
        if not self.frame:
            return None
        self._status_label = wx.StaticText(self.frame, label="")
        self._status_label.SetForegroundColour(wx.Colour(200, 200, 200))
        return self._status_label

    def set_status(self, text, timeout_ms=0):
        if self._status_label:
            self._status_label.SetLabel(text)
            if timeout_ms > 0:
                wx.CallLater(timeout_ms, self._clear_status)

    def _clear_status(self):
        if self._status_label:
            self._status_label.SetLabel("")

    # ── Theme inheritance (appearance config) ─────────────────────────────

    def _apply_appearance(self):
        ac = getattr(getattr(self.api, 'desktop', None), 'appearance_config', {})
        if not ac or not self.frame:
            return
        bg = ac.get("desktop_bg", "#000000")
        self.frame.SetBackgroundColour(wx.Colour(bg))

    # ── Window position memory ────────────────────────────────────────────

    def _winpos_path(self):
        return self.api.get_data_path(f"winpos_{self.__class__.__name__}.json")

    def _save_position(self):
        if not self.frame:
            return
        try:
            pos = self.frame.GetPosition()
            size = self.frame.GetSize()
            with open(self._winpos_path(), "w") as f:
                json.dump({"x": pos.x, "y": pos.y, "w": size.width, "h": size.height}, f)
        except Exception:
            pass

    def _restore_position(self):
        if not self.frame:
            return
        try:
            path = self._winpos_path()
            if os.path.exists(path):
                with open(path) as f:
                    d = json.load(f)
                    self.frame.SetPosition(wx.Point(d["x"], d["y"]))
                    self.frame.SetSize(d["w"], d["h"])
        except Exception:
            pass

    # ── Multiple timers ───────────────────────────────────────────────────

    def add_timer(self, interval_ms, callback):
        if self.frame:
            t = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda evt: self._safe_call(callback), t)
            t.Start(interval_ms)
            self._timers.append(t)
            return t
        return None

    def stop_timers(self):
        for t in self._timers:
            try:
                t.Stop()
            except Exception:
                pass
        self._timers.clear()

    # ── Frame lifecycle ───────────────────────────────────────────────────

    def _dpi(self):
        if self._dpi_scale is None:
            self._dpi_scale = wx.ScreenDC().GetPPI()[0] / 96.0 if wx.ScreenDC().GetPPI()[0] else 1.0
        return self._dpi_scale

    def scale(self, value):
        return int(value * self._dpi())

    def _create_frame(self, title, size=(600, 450)):
        scaled = (self.scale(size[0]), self.scale(size[1]))
        self.frame = wx.Frame(None, title=title, size=scaled)
        self.frame.SetName(title)
        self._apply_appearance()
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Bind(wx.EVT_SET_FOCUS, lambda evt: self.on_focus())
        self.frame.Bind(wx.EVT_KILL_FOCUS, lambda evt: self.on_blur())
        if self._tick_interval > 0 and self._tick_timer is None:
            self._tick_timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda evt: self.on_tick(), self._tick_timer)
            self._tick_timer.Start(self._tick_interval)
        self._apply_accelerators()
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_nav_key)
        self.restore_winpos = wx.CallAfter(self._restore_position)
        return self.frame

    def _show_app(self, focus_ctrl=None):
        if self.frame:
            self.frame.Show()
            if focus_ctrl:
                focus_ctrl.SetFocus()

    def on_key(self, event):
        return False

    def _on_nav_key(self, event):
        if self.on_key(event):
            return
        if event.ControlDown():
            kc = event.GetKeyCode()
            d = self.api.desktop
            if kc == wx.WXK_LEFT:
                wx.CallAfter(d.nav_back); return
            elif kc == wx.WXK_RIGHT:
                wx.CallAfter(d.nav_overview); return
            elif kc == wx.WXK_DOWN:
                wx.CallAfter(d.nav_home); return
            elif kc == wx.WXK_UP:
                wx.CallAfter(d.nav_notifications); return
        event.Skip()

    # ── Terminal / helpers ────────────────────────────────────────────────

    def terminal_input(self, command):
        parts = command.split(maxsplit=1)
        action = parts[0].lower() if parts else ""
        cmds = self.get_terminal_commands()
        if action in ("help", "?"):
            if cmds:
                self.api.terminal_output(f"{self.name} commands:")
                for cmd, desc in cmds.items():
                    self.api.terminal_output(f"  {cmd}: {desc}")
            else:
                self.api.terminal_output(f"{self.name} has no terminal commands.")
        elif action:
            self.api.terminal_output(f"Unknown command: {action}. Type 'help' for {self.name} commands.")

    def get_terminal_commands(self):
        return {}

    def speak(self, text, interrupt=True):
        self.api.speak(text, interrupt)

    def play_sound(self, sound_type):
        try:
            self.api.play_sound(sound_type)
        except Exception:
            pass


class SystemAPI:
    """Bridge between apps and the OS core."""
    def __init__(self, desktop, kernel, engine, sounds):
        self.desktop = desktop
        self.kernel = kernel
        self.engine = engine
        self.sounds = sounds
        self.network = NetworkService()
        self.data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_data_path(self, filename):
        return os.path.join(self.data_dir, filename)

    def get_vfs(self):
        return self.kernel

    def terminal_output(self, text):
        if hasattr(self.kernel, 'output_callback') and self.kernel.output_callback:
            self.kernel.output_callback(text)

    def speak(self, text, interrupt=True):
        self.engine.speak(text, interrupt)

    def play_sound(self, sound_type):
        self.sounds.play(sound_type)

    def notify(self, title: str, message: str, level: str = 'info'):
        full_message = f"{title}. {message}"
        if level == 'warning':
            full_message = f"Warning: {full_message}"
        elif level == 'error':
            full_message = f"Error: {full_message}"
        self.speak(full_message)
        if hasattr(self.desktop, 'push_notification'):
            self.desktop.push_notification(title, message, level)

    def launch_app(self, app_name: str, **kwargs):
        try:
            app_class = None
            for loaded_app in getattr(self.desktop, "apps", []):
                if loaded_app.__class__.__name__ == app_name or loaded_app.name == app_name:
                    app_class = loaded_app.__class__
                    break
            if not app_class:
                apps_dir = os.path.join(os.getcwd(), "apps")
                for filename in os.listdir(apps_dir):
                    if filename.endswith(".py") and filename != "__init__.py":
                        module_path = f"apps.{filename[:-3]}"
                        try:
                            module = importlib.import_module(module_path)
                            for attr in dir(module):
                                cls = getattr(module, attr)
                                if isinstance(cls, type) and issubclass(cls, BlindApp) and cls is not BlindApp:
                                    if cls.__name__ == app_name:
                                        app_class = cls
                                        break
                            if app_class: break
                        except Exception:
                            continue
            if not app_class:
                self.speak(f"Application '{app_name}' not found.")
                return
            instance = app_class(self)
            if hasattr(self.desktop, 'open_apps'):
                self.desktop.open_apps.append(instance)
            if kwargs:
                wx.CallAfter(instance.run, **kwargs)
            else:
                wx.CallAfter(instance.run)
            self.speak(f"Launched {getattr(instance, 'name', app_name)}.", interrupt=False)
        except Exception as e:
            self.speak(f"Failed to launch {app_name}: {e}")
