import wx
import speech
import os
import subprocess # For executing files
import importlib # Import importlib for dynamic module loading

from message_service import MessageService

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

    def terminal_input(self, command):
        """Override to handle input commands from the system terminal."""
        self.api.speak(f"Command received: {command}")

    def get_terminal_commands(self):
        """Override to return a dictionary of command descriptions."""
        return {}

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
        self.message_service = MessageService(self)
        self.data_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def get_data_path(self, filename):
        return os.path.join(self.data_dir, filename)

    def get_vfs(self):
        return self.kernel

    def terminal_output(self, text):
        """Sends text to the global system terminal output, if active."""
        if hasattr(self.kernel, 'output_callback') and self.kernel.output_callback:
            self.kernel.output_callback(text)

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

    def launch_app(self, app_name: str, **kwargs):
        """
        Launches an application by its name.
        Searches for the app class in the 'apps/' directory.
        """
        try:
            app_class = None
            
            # 1. Check already loaded apps in desktop
            for loaded_app in getattr(self.desktop, "apps", []):
                if loaded_app.__class__.__name__ == app_name or loaded_app.name == app_name:
                    app_class = loaded_app.__class__
                    break

            # 2. Dynamic discovery if not found
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
                        except Exception: continue

            if not app_class:
                self.speak(f"Application '{app_name}' not found.")
                return

            # Instantiate with API object, and pass launch kwargs to run().
            instance = app_class(self)
            # Use CallAfter to ensure UI creation happens on the main thread
            if kwargs:
                wx.CallAfter(instance.run, **kwargs)
            else:
                wx.CallAfter(instance.run)
            
            self.speak(f"Launched {getattr(instance, 'name', app_name)}.", interrupt=False)

        except Exception as e:
            self.speak(f"Failed to launch {app_name}: {e}")
