import wx
import json
import os
from api import BlindApp

class SoundSettingsApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Sound Themes"
        self.description = "Change the system sound effects."
        self.help_text = "Use arrow keys to preview themes, and Enter to apply."
        self.docs = "Sound Themes allows you to change the auditory style of PyOS. Available: Modern, Retro, Classic."

    def run(self):
        self.frame = wx.Frame(None, title="Sound Themes", size=(400, 300))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(panel, label="Select Sound Theme:")
        label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(label, 0, wx.ALL | wx.CENTER, 20)
        themes = self.api.sounds.get_available_themes()
        self.list = wx.ListBox(panel, choices=themes, style=wx.LB_SINGLE)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        current = self.api.sounds.current_theme
        if current in themes: self.list.SetSelection(themes.index(current))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        select_btn = wx.Button(panel, label="Apply and Close")
        sizer.Add(select_btn, 0, wx.ALL | wx.CENTER, 20)
        panel.SetSizer(sizer)
        self.list.Bind(wx.EVT_LISTBOX, self.on_preview)
        select_btn.Bind(wx.EVT_BUTTON, self.on_apply)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak(f"Sound Themes opened. Current: {current}.")
        self.list.SetFocus()

    def on_preview(self, event):
        theme_name = self.list.GetStringSelection()
        self.api.sounds.current_theme = theme_name
        self.api.play_sound("startup")
        self.api.speak(theme_name)

    def on_apply(self, event):
        theme_name = self.list.GetStringSelection()
        self.api.sounds.save_theme_name(theme_name)
        self.api.speak(f"Theme {theme_name} applied.")
        self.on_close()

class ThemeCreatorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Theme Creator"
        self.description = "Create your own sound theme."
        # Updated docs to reflect file support and new event types
        self.docs = "Theme Creator allows you to define custom tones or sound file paths for system events like startup, navigation, alerts, launch, close, alarms, and timers." 

        self.frame = wx.Frame(None, title="Theme Creator", size=(400, 400))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.label = wx.StaticText(panel, label="Enter name for new theme:")
        self.label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.label.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.label, 0, wx.ALL | wx.CENTER, 10)
        
        # Initial input for theme name
        self.input_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.input_ctrl.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 10)
        
        self.btn = wx.Button(panel, label="Next")
        sizer.Add(self.btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(sizer)
        
        # State variables for theme creation flow
        self.step = 0
        self.current_event_index = 0 # To track which sound event we are configuring
        # Added "alarm" and "timer" to the events list
        self.events = ["startup", "nav", "alert", "launch", "close", "alarm", "timer"] 
        self.new_theme = {} # Will store tones (list of lists) or file paths (string)
        self.theme_name = ""
        self.current_event = ""
        self.sound_choice_mode = "" # To store 'tones' or 'file'

        self.btn.Bind(wx.EVT_BUTTON, self.on_next)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_next)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.speak("Theme Creator opened. Enter a name for your theme.")
        self.input_ctrl.SetFocus()

    def on_next(self, event=None):
        val = self.input_ctrl.GetValue().strip()
        self.input_ctrl.Clear()
        if not val: return

        if self.step == 0: # Theme name input
            self.theme_name = val
            self.current_event = self.events[self.current_event_index]
            self.label.SetLabel(f"For the {self.current_event.capitalize()} sound, choose: tones or file?")
            self.api.speak(f"For the {self.current_event} sound, do you want to use tones or a file? Type 'tones' or 'file'.")
            self.step = 1 # Next step is to choose sound type

        elif self.step == 1: # Choose sound type (tones/file) for current event
            self.sound_choice_mode = val.lower()
            if self.sound_choice_mode == "tones":
                self.label.SetLabel(f"Enter frequency for {self.current_event.capitalize()} beep:")
                self.api.speak(f"Enter frequency for {self.current_event} beep (e.g., 500).")
                self.step = 2 # Next step is to input tone frequency
            elif self.sound_choice_mode == "file":
                # Open file dialog for audio files
                wildcard = "Audio files (*.wav;*.mp3;*.ogg;*.flac)|*.wav;*.mp3;*.ogg;*.flac|WAV files (*.wav)|*.wav|MP3 files (*.mp3)|*.mp3|OGG files (*.ogg)|*.ogg|FLAC files (*.flac)|*.flac"
                dlg = wx.FileDialog(self.frame, "Choose an audio file", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
                if dlg.ShowModal() == wx.ID_OK:
                    file_path = dlg.GetPath()
                    self.new_theme[self.current_event] = file_path
                    self.api.speak(f"{self.current_event.capitalize()} sound set to file: {file_path}")
                    self.advance_to_next_event()
                else:
                    self.api.speak("File selection cancelled. Please choose 'tones' or 'file'.")
                    # Stay on step 1 to re-prompt for choice
            else:
                self.api.speak("Invalid choice. Please type 'tones' or 'file'.")
                # Stay on step 1 to re-prompt for choice

        elif self.step == 2: # Input for tone frequency
            try:
                freq = int(val)
                # Default duration for tones, could be made configurable later
                duration = 300 if self.current_event == "startup" else (50 if self.current_event == "nav" else 500)
                self.new_theme[self.current_event] = [(freq, duration)]
                self.api.speak(f"{self.current_event.capitalize()} tone set.")
                self.advance_to_next_event()
            except ValueError:
                self.api.speak("Invalid frequency. Please enter a number.")
                # Stay on step 2 to re-prompt for frequency

    def advance_to_next_event(self):
        self.current_event_index += 1
        if self.current_event_index < len(self.events):
            self.current_event = self.events[self.current_event_index]
            self.step = 1 # Reset to choose sound type for the next event
            prompt_message = f"For the {self.current_event.capitalize()} sound, do you want to use tones or a file? (tones/file):"
            self.api.speak(prompt_message)
            self.label.SetLabel(f"Choose sound type for {self.current_event.capitalize()}: tones or file?")
        else:
            # All events processed, finalize theme
            self.finalize_theme()

    def finalize_theme(self):
        # Set default tones for launch/close if they weren't configured interactively
        # These are hardcoded defaults, could be made configurable in a more robust app.
        if "launch" not in self.new_theme or not self.new_theme["launch"]:
             self.new_theme["launch"] = [(800, 100)]
        if "close" not in self.new_theme or not self.new_theme["close"]:
             self.new_theme["close"] = [(400, 100)]

        if self.theme_name and self.new_theme:
            # Add the new theme to the in-memory themes dictionary
            self.api.sounds.themes[self.theme_name] = self.new_theme
            
            # To make this theme persistent, we need to save it to user_themes.json.
            # Call the newly implemented save_custom_themes method.
            self.api.sounds.save_custom_themes() 

            # Apply the new theme immediately as the current theme
            self.api.sounds.save_theme_name(self.theme_name)
            self.api.speak(f"Theme {self.theme_name} created and applied!")
        else:
            self.api.speak("Theme creation failed. Please ensure all required inputs were provided.")
            
        self.frame.Destroy() # Close the frame after completion or failure

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)