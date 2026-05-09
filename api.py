import wx
import speech
import os

class BlindApp:
    """Base class for all BlindOS applications."""
    def __init__(self, api):
        self.api = api
        self.name = "Abstract App"
        self.description = "Base application class"
        self.help_text = "No help available for this app."
        self.docs = "No documentation available."
        self.frame = None

    def run(self):
        """Override to launch the app's UI."""
        pass

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)

    def speak(self, text, interrupt=True):
        """Helper to speak text via system engine."""
        self.api.engine.speak(text, interrupt)

class SystemAPI:
    """Bridge between apps and the OS core."""
    def __init__(self, desktop, kernel, engine, sounds):
        self.desktop = desktop
        self.kernel = kernel
        self.engine = engine
        self.sounds = sounds
        self.data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_data_path(self, filename):
        return os.path.join(self.data_dir, filename)

    def get_vfs(self):
        return self.kernel

    def speak(self, text, interrupt=True):
        self.engine.speak(text, interrupt)

    def play_sound(self, sound_type):
        self.sounds.play(sound_type)

    def notify(self, title: str, message: str, level: str = 'info'):
        """
        Sends a notification to the user.
        Currently, this only supports spoken notifications.
        Level can be 'info', 'warning', or 'error'.
        """
        full_message = f"{title}. {message}"
        if level == 'warning':
            full_message = f"Warning: {full_message}"
        elif level == 'error':
            full_message = f"Error: {full_message}"
        
        self.speak(full_message)
        # Future enhancement: Add visual notification if GUI is available.
        # For example, using wx.MessageDialog, but this requires context of the main window.
        # if self.desktop.main_frame: # Assuming desktop has a reference to the main frame
        #     wx.CallAfter(wx.MessageDialog, self.desktop.main_frame, message, title, style=wx.OK | (wx.ICON_WARNING if level == 'warning' else (wx.ICON_ERROR if level == 'error' else wx.ICON_INFORMATION))).ShowModal()

