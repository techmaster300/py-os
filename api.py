import wx
import speech
import os
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

    def run(self):
        """Override to launch the app's UI."""
        pass

    def on_focus(self):
        """Called when the app window gains focus."""

    def on_blur(self):
        """Called when the app window loses focus."""

    def on_tick(self):
        """Called every _tick_interval ms if _tick_interval > 0."""

    def on_open(self, filepath=None):
        """Override to handle being launched with a file."""

    def confirm(self, message, title="Confirm"):
        """Show a Yes/No dialog. Returns True for Yes."""
        dlg = wx.MessageDialog(self.frame or None, message, title, wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result

    def alert(self, message, title="Alert"):
        """Show an information dialog."""
        dlg = wx.MessageDialog(self.frame or None, message, title, wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def prompt(self, message, default="", title="Input"):
        """Show a text input dialog. Returns the value or None if cancelled."""
        dlg = wx.TextEntryDialog(self.frame or None, message, title, default)
        if dlg.ShowModal() == wx.ID_OK:
            result = dlg.GetValue()
            dlg.Destroy()
            return result
        dlg.Destroy()
        return None

    def choice(self, message, choices, title="Select"):
        """Show a choice dialog. Returns the selected string or None."""
        dlg = wx.SingleChoiceDialog(self.frame or None, message, title, choices)
        if dlg.ShowModal() == wx.ID_OK:
            result = dlg.GetStringSelection()
            dlg.Destroy()
            return result
        dlg.Destroy()
        return None

    def notify(self, title, message, level='info'):
        """Send a notification to the user."""
        self.api.notify(title, message, level)

    def bind_accelerator(self, flags, key_code, command_id, handler, description=""):
        """Register an accelerator table entry."""
        self._accel_entries.append((flags, key_code, command_id, handler, description))

    def _apply_accelerators(self):
        """Apply all registered accelerators to the frame."""
        if not self._accel_entries or not self.frame:
            return
        entries = []
        for flags, key, cmd_id, handler, desc in self._accel_entries:
            entries.append((flags, key, cmd_id))
            self.frame.Bind(wx.EVT_MENU, handler, id=cmd_id)
        if entries:
            self.frame.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def _create_frame(self, title, size=(600, 450)):
        """Create a standard app frame with dark theme and close binding."""
        self.frame = wx.Frame(None, title=title, size=size)
        self.frame.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Bind(wx.EVT_SET_FOCUS, lambda evt: self.on_focus())
        self.frame.Bind(wx.EVT_KILL_FOCUS, lambda evt: self.on_blur())
        if self._tick_interval > 0:
            self._tick_timer = wx.Timer(self.frame)
            self.frame.Bind(wx.EVT_TIMER, lambda evt: self.on_tick(), self._tick_timer)
            self._tick_timer.Start(self._tick_interval)
        self._apply_accelerators()
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_nav_key)
        return self.frame

    def _show_app(self, focus_ctrl=None):
        if self.frame:
            self.frame.Show()
            if focus_ctrl:
                focus_ctrl.SetFocus()

    def terminal_input(self, command):
        """Override to handle input commands from the system terminal."""
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
        """Override to return a dictionary of command descriptions."""
        return {}

    def speak(self, text, interrupt=True):
        """Helper to speak text via system engine."""
        self.api.speak(text, interrupt)

    def play_sound(self, sound_type):
        """Helper to play a system sound."""
        try:
            self.api.play_sound(sound_type)
        except Exception:
            pass

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        if self._tick_timer:
            self._tick_timer.Stop()
            self._tick_timer = None
        if self.frame:
            self.frame.Destroy()
            self.frame = None
        self.play_sound("close")
        self.api.desktop.on_app_closed(self)

    def _on_nav_key(self, event):
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
