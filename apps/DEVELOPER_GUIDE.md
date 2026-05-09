# PyOS Developer Guide

PyOS is a modular, accessible operating system simulator for the blind. This guide explains how to create your own applications (plugins).

## 1. Getting Started
All apps are Python files located in the `/apps` directory. PyOS automatically discovers and loads any class that inherits from `BlindApp`.

## 2. Basic App Structure
Create a new file in `apps/my_app.py`:

```python
import wx
from api import BlindApp

class MyApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "My Application"
        self.description = "A short description for the screen reader."
        self.help_text = "Press Enter to perform the main action."
        self.docs = "This app demonstrates the basic structure of a PyOS plugin."

    def run(self):
        self.frame = wx.Frame(None, title=self.name, size=(400, 300))
        panel = wx.Panel(self.frame)
        btn = wx.Button(panel, label="Click Me")
        btn.Bind(wx.EVT_BUTTON, self.on_click)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("My application is now open.")

    def on_click(self, event):
        self.api.speak("You clicked the button!")
```

## 3. The System API (`self.api`)
| Method | Description |
| :--- | :--- |
| `speak(text, interrupt=True)` | Speaks text via NVDA or standard TTS. |
| `play_sound(sound_type)` | Plays a themed sound (`nav`, `launch`, `close`, `alert`). |
| `get_data_path(filename)` | Returns a path to a file in the user's `.py-os` folder. |
| `get_vfs()` | Returns the Virtual File System kernel. |

## 4. Special Features
- **F1 (Help)**: PyOS automatically reads your app's `self.help_text` when the user presses **F1**.
- **Ctrl+D (Docs)**: PyOS reads your app's `self.docs` when the user presses **Ctrl+D**.
- **Sound Themes**: Users can create custom sounds in the **Theme Creator**. Use `self.api.play_sound()` to stay consistent with the user's chosen theme.
