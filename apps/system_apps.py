import wx
import os
import datetime
from api import BlindApp
# Assuming LoonaConfig and ConfigStore are still relevant for general settings persistence if needed,
# but they are not directly used by TextEditorApp in this basic implementation.

class SettingsApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "System Settings"
        self.description = "Configure voice speed and high contrast."
        self.help_text = "Use Tab to navigate controls, and Enter to save."
        self.docs = "Settings allows you to customize the OS behavior. Voice speed can be adjusted from 50 to 400."

    def run(self):
        self.frame = wx.Frame(None, title="Settings", size=(400, 300))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(30, 30, 30))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(panel, label="Voice Speed:")
        label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(label, 0, wx.ALL, 10)
        
        self.speed_slider = wx.Slider(panel, value=200, minValue=50, maxValue=400, style=wx.SL_HORIZONTAL)
        sizer.Add(self.speed_slider, 0, wx.EXPAND | wx.ALL, 10)
        
        close_btn = wx.Button(panel, label="Save and Close")
        sizer.Add(close_btn, 0, wx.ALL | wx.CENTER, 20)
        
        panel.SetSizer(sizer)
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("Settings opened.")

class FileExplorerApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "File Explorer"
        self.description = "Browse your files."
        self.help_text = "Use arrow keys to browse files and directories. Enter to open directories or files."
        self.docs = "File Explorer allows you to browse the host file system. Navigate directories and open files."
        self.current_dir = os.getcwd() # Start in the current working directory

    def run(self):
        self.frame = wx.Frame(None, title=f"File Explorer - {self.current_dir}", size=(500, 400))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.refresh_files()
        
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open) # Double-click to open
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key_down) # Handle Enter key for navigation
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("File Explorer opened.")
        self.list.SetFocus()

    def refresh_files(self):
        try:
            items = os.listdir(self.current_dir)
            # Sort items to have directories first, then files, alphabetically
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            self.list.Set([f"[D] {item}" if os.path.isdir(os.path.join(self.current_dir, item)) else item for item in items])
            self.frame.SetTitle(f"File Explorer - {self.current_dir}")
        except Exception as e:
            self.api.speak(f"Error accessing directory: {e}")
            self.list.Set(["Error loading directory"])
            self.current_dir = os.path.expanduser("~") # Reset to home directory on error

    def on_open(self, event):
        selected_item = self.list.GetStringSelection()
        if not selected_item:
            return

        # Remove directory indicator if present
        if selected_item.startswith("[D] "):
            selected_item = selected_item[4:]

        full_path = os.path.join(self.current_dir, selected_item)

        if os.path.isdir(full_path):
            self.current_dir = full_path
            self.refresh_files()
            self.api.speak(f"Navigated to {selected_item}")
        elif os.path.isfile(full_path):
            # For files, we might want to open them with a default application
            # For now, just announce the file and its path
            self.api.speak(f"Selected file: {selected_item}")
            # Potentially open file with TextEditorApp or default viewer if implemented
            # Example: self.api.launch_app("TextEditorApp", file_path=full_path)
            # For now, we'll just speak it.

    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_RETURN:
            self.on_open(None) # Treat Enter key press as opening the selected item
        event.Skip() # Allow default handling for other keys

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)

class ClockApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Clock"
        self.description = "Check the current time and date."
        self.help_text = "This app announces the time and closes automatically."
        self.docs = "Clock provides current system time and date information."

    def run(self):
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        msg = f"It is currently {time_str} on {date_str}."
        self.api.speak(msg)
        wx.CallLater(3000, self.on_close)

class CalculatorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Calculator"
        self.description = "Basic math calculator."
        self.help_text = "Type an expression like '2 + 2' and press Enter."
        self.docs = "Calculator supports basic arithmetic: addition (+), subtraction (-), multiplication (*), and division (/)."

    def run(self):
        self.frame = wx.Frame(None, title="Calculator", size=(400, 200))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.input_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 20)
        
        panel.SetSizer(sizer)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_calc)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.speak("Calculator opened. Enter an expression.")
        self.input_ctrl.SetFocus()

    def on_calc(self, event):
        expr = self.input_ctrl.GetValue()
        self.input_ctrl.Clear()
        try:
            # Dangerous but for a simulator it's okay. 
            # In real OS we'd use a safe math parser.
            result = eval(expr, {"__builtins__": None}, {})
            msg = f"Result: {result}"
        except Exception:
            msg = "Error: Invalid expression."
        
        self.api.speak(msg)

class TextEditorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Text Editor"
        self.description = "A simple text editor."
        self.help_text = "Use standard text editing shortcuts. Save or Open files."
        self.docs = "The Text Editor allows you to create, open, edit, and save text files."
        self.frame = None
        self.text_ctrl = None
        self.current_file_path = None

    def run(self):
        self.frame = wx.Frame(None, title="Text Editor", size=(600, 500))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(25, 25, 25))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH)
        self.text_ctrl.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.text_ctrl.SetForegroundColour(wx.Colour(220, 220, 220))
        main_sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        open_btn = wx.Button(panel, label="Open")
        save_btn = wx.Button(panel, label="Save")
        close_btn = wx.Button(panel, label="Close")
        
        button_sizer.Add(open_btn, 0, wx.ALL, 5)
        button_sizer.Add(save_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1) # Push close button to the right
        button_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        
        open_btn.Bind(wx.EVT_BUTTON, self.on_open)
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.speak("Text Editor opened.")
        self.text_ctrl.SetFocus()

    def on_open(self, event):
        dialog = wx.FileDialog(self.frame, "Open Text File", wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            self.current_file_path = dialog.GetPath()
            try:
                with open(self.current_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_ctrl.SetValue(content)
                    self.frame.SetTitle(f"Text Editor - {os.path.basename(self.current_file_path)}")
                    self.api.speak(f"Opened file: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                self.api.speak(f"Error opening file: {e}")
                self.current_file_path = None
                self.frame.SetTitle("Text Editor")
        dialog.Destroy()

    def on_save(self, event):
        if self.current_file_path:
            # If a file is already open, save directly
            try:
                content = self.text_ctrl.GetValue()
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.api.speak(f"File saved: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                self.api.speak(f"Error saving file: {e}")
        else:
            # If no file is open, prompt for save as
            self.on_save_as(event)

    def on_save_as(self, event):
        dialog = wx.FileDialog(self.frame, "Save Text File As", wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            self.current_file_path = dialog.GetPath()
            try:
                content = self.text_ctrl.GetValue()
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.frame.SetTitle(f"Text Editor - {os.path.basename(self.current_file_path)}")
                self.api.speak(f"File saved as: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                self.api.speak(f"Error saving file: {e}")
        dialog.Destroy()

    def on_close(self, event=None):
        """Cleanup and return focus to desktop."""
        # Basic check for unsaved changes could be added here
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
