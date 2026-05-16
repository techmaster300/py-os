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
        Searches for the app in known locations (e.g., 'apps.<module>.<ClassName>').
        Passes keyword arguments to the app's constructor or run method.
        """
        try:
            app_class = None
            # Prefer loaded desktop app classes for reliable launches.
            for loaded_app in getattr(self.desktop, "apps", []):
                if loaded_app.__class__.__name__ == app_name:
                    app_class = loaded_app.__class__
                    break

            # Fallback dynamic imports if not found in loaded apps.
            if not app_class:
                possible_module_paths = [
                    f"apps.{app_name.lower()}",
                    "apps.system_apps",
                    "apps.audio_recorder",
                    "apps.sound_settings",
                ]
                for module_path in possible_module_paths:
                    try:
                        module = importlib.import_module(module_path)
                        app_class = getattr(module, app_name, None)
                        if app_class:
                            break
                    except ImportError:
                        continue
                    except AttributeError:
                        continue

            if not app_class:
                self.speak(f"Application '{app_name}' not found or could not be loaded.")
                return

            # Instantiate with API object, and pass launch kwargs to run().
            instance = app_class(self)
            if kwargs:
                instance.run(**kwargs)
            else:
                instance.run()
            self.speak(f"Launched {app_name}.", interrupt=False)

        except Exception as e:
            self.speak(f"Failed to launch {app_name}: {e}")
