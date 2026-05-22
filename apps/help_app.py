import wx
import os
from api import BlindApp

class HelpApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Help and Documentation"
        self.description = "Learn how to use PyOS and create your own apps."
        self.help_text = "Use the list to select a topic and press Enter to read it."
        self.docs = "This app provides comprehensive guides for both users and developers of PyOS."
        
        self.topics = {
            "User Guide: Getting Started": (
                "Welcome to PyOS! PyOS is designed for accessibility. "
                "Use the Tab key to move between apps on the desktop and press Enter to launch them. "
                "Press F1 at any time to hear help for the active app, or Ctrl+D to hear its full documentation."
            ),
            "User Guide: Keyboard Shortcuts": (
                "General Shortcuts:\n"
                "Tab: Navigate between buttons and apps.\n"
                "Enter: Launch or activate the selected item.\n"
                "F1: Speak help for the current app.\n"
                "Ctrl+D: Speak full documentation for the current app.\n"
                "Alt+F4: Close the current app.\n\n"
                "File Explorer Shortcuts:\n"
                "Backspace: Go up one folder level.\n"
                "Alt + Left: Go back in history."
            ),
            "Developer: Creating an App": (
                "To create a PyOS app, add a Python file to the 'apps' folder. "
                "Your class must inherit from 'BlindApp' in 'api.py'. "
                "Implement a 'run()' method to build your UI using wxPython. "
                "Example files can be found in the 'apps' directory."
            ),
            "Developer: Using the API": (
                "Use 'self.api.speak(text)' to talk to the user. "
                "Use 'self.api.play_sound(name)' to play system sounds like 'nav', 'launch', or 'alert'. "
                "Check DEVELOPER_GUIDE.md in the apps folder for the full API table."
            ),
            "About PyOS": (
                "PyOS is an accessible operating system simulator built with Python and wxPython. "
                "It aims to provide a safe and powerful environment for blind and visually impaired users."
            )
        }

    def run(self):
        self.frame = wx.Frame(None, title="Help and Documentation", size=(600, 500))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        title = wx.StaticText(panel, label="Help Center")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)
        
        topics_label = wx.StaticText(panel, label="Select a Topic:")
        topics_label.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(topics_label, 0, wx.LEFT | wx.TOP, 10)

        self.list = wx.ListBox(panel, choices=list(self.topics.keys()), style=wx.LB_SINGLE)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        self.list.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_MEDIUM))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        
        read_btn = wx.Button(panel, label="Read Topic")
        read_btn.SetDefault()
        sizer.Add(read_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(sizer)
        
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_read)
        read_btn.Bind(wx.EVT_BUTTON, self.on_read)
        self.list.Bind(wx.EVT_LISTBOX, self.on_select)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.speak("Help Center opened. Select a topic to read.")
        self.list.SetFocus()

    def on_select(self, event):
        topic = self.list.GetStringSelection()
        self.api.speak(topic)

    def get_terminal_commands(self):
        return {
            "list": "List all available help topics.",
            "read <topic>": "Read the content of a specific topic."
        }

    def terminal_input(self, command):
        parts = command.split(maxsplit=1)
        if not parts: return
        action = parts[0].lower()
        
        if action == "list":
            for topic in self.topics.keys():
                self.api.terminal_output(topic)
        elif action == "read":
            if len(parts) > 1:
                topic_query = parts[1].lower()
                found = False
                for topic in self.topics:
                    if topic_query in topic.lower():
                        self.api.terminal_output(f"{topic}: {self.topics[topic]}")
                        found = True
                if not found:
                    self.api.terminal_output(f"Topic '{parts[1]}' not found.")
            else:
                self.api.terminal_output("Specify a topic: read <topic>")
        else:
            self.api.terminal_output("Unknown command. Available: list, read")
