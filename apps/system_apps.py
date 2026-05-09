import wx
import os
import datetime
import subprocess # For executing files
import importlib # For dynamic module loading
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
        
        update_btn = wx.Button(panel, label="Check for Updates")
        update_btn.Bind(wx.EVT_BUTTON, self.check_updates)
        sizer.Add(update_btn, 0, wx.ALL | wx.CENTER, 10)

        close_btn = wx.Button(panel, label="Save and Close")
        sizer.Add(close_btn, 0, wx.ALL | wx.CENTER, 20)
        
        panel.SetSizer(sizer)
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("Settings opened.")

    def check_updates(self, event):
        self.api.speak("Checking for updates...")
        try:
            # Running git pull from the specific repository
            # First, ensure we are tracking the correct remote, then pull
            subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/wasilewsk/py-os.git"], check=True)
            result = subprocess.run(["git", "pull", "origin", "master"], capture_output=True, text=True, check=True)
            self.api.speak("Update completed successfully.")
        except subprocess.CalledProcessError as e:
            self.api.speak(f"Update failed: {e.stderr}")
        except Exception as e:
            self.api.speak(f"Error during update: {e}")

class FileExplorerApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "File Explorer"
        self.description = "Browse your files."
        self.help_text = "Use navigation buttons, address bar, arrow keys, or Enter to browse files and directories. Double-click or Enter to open."
        self.docs = "File Explorer allows you to browse the host file system. Navigate directories, open text files with the Text Editor, and execute programs."
        self.current_dir = os.getcwd() 
        self.history = [] 
        self.history_index = -1
        self.forward_history = [] 

    def run(self):
        self.frame = wx.Frame(None, title=f"File Explorer - {self.current_dir}", size=(600, 500))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Navigation Toolbar ---
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_button = wx.Button(panel, label="< Back")
        self.forward_button = wx.Button(panel, label="Forward >")
        self.address_bar = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.address_bar.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.address_bar.SetForegroundColour(wx.Colour(255, 255, 255))

        nav_sizer.Add(self.back_button, 0, wx.ALL, 5) 
        nav_sizer.Add(self.forward_button, 0, wx.ALL, 5)
        nav_sizer.Add(self.address_bar, 1, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(nav_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- File List ---
        self.list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        main_sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        
        # --- Buttons ---
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        refresh_btn = wx.Button(panel, label="Refresh")
        close_btn = wx.Button(panel, label="Close")
        
        button_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        main_sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        
        # Bindings
        self.back_button.Bind(wx.EVT_BUTTON, self.go_back)
        self.forward_button.Bind(wx.EVT_BUTTON, self.go_forward)
        self.address_bar.Bind(wx.EVT_TEXT_ENTER, self.go_to_address)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        refresh_btn.Bind(wx.EVT_BUTTON, lambda e: self.go_to_path(self.current_dir))
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.speak("File Explorer opened.")
        self.list.SetFocus()

    def go_to_path(self, path):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            self.api.speak(f"Path not found: {path}")
            return
        if self.current_dir != path:
            self.history.append(self.current_dir)
            self.forward_history = []
            self.history_index = len(self.history) - 1
            if len(self.history) > 50: self.history.pop(0)
        self.current_dir = path
        self.refresh_files()
        self.address_bar.SetValue(self.current_dir)
        self.update_navigation_buttons()
        self.api.speak(f"Navigated to {os.path.basename(path)}")

    def go_back(self, event):
        if self.history_index >= 0 and len(self.history) > 0:
            if self.current_dir and self.current_dir != self.history[self.history_index]:
                self.forward_history.append(self.current_dir)
                if len(self.forward_history) > 50: self.forward_history.pop(0)
            self.current_dir = self.history[self.history_index]
            self.history_index -= 1
            self.refresh_files()
            self.address_bar.SetValue(self.current_dir)
            self.api.speak("Going back")
            self.update_navigation_buttons()
        else:
            self.api.speak("Cannot go back further.")
            
    def go_forward(self, event):
        if self.history_index + 1 < len(self.history):
            self.history_index += 1
            self.current_dir = self.history[self.history_index]
            self.refresh_files()
            self.address_bar.SetValue(self.current_dir)
            self.api.speak("Going forward")
            self.update_navigation_buttons()
        else:
            self.api.speak("Cannot go forward.")

    def go_to_address(self, event):
        new_path = self.address_bar.GetValue()
        self.go_to_path(new_path)

    def update_navigation_buttons(self):
        self.back_button.Enable(self.history_index >= 0)
        self.forward_button.Enable(self.history_index + 1 < len(self.history))

    def refresh_files(self):
        try:
            items = os.listdir(self.current_dir)
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            display_items = []
            for item in items:
                full_path = os.path.join(self.current_dir, item)
                display_items.append(f"[D] {item}" if os.path.isdir(full_path) else item)
            self.list.Set(display_items)
            self.frame.SetTitle(f"File Explorer - {self.current_dir}")
        except OSError as e:
            self.api.speak(f"Error accessing directory: {e}")
            self.list.Set(["Error loading directory"])
            self.current_dir = os.path.expanduser("~")
            self.refresh_files()

    def on_open(self, event):
        selected_item = self.list.GetStringSelection()
        if not selected_item: return
        item_name = selected_item[4:] if selected_item.startswith("[D] ") else selected_item
        full_path = os.path.join(self.current_dir, item_name)
        if os.path.isdir(full_path):
            self.go_to_path(full_path)
        elif os.path.isfile(full_path):
            self.api.speak(f"Opening file: {item_name}")
            if item_name.lower().endswith(".txt"):
                try:
                    self.api.launch_app("TextEditorApp", file_path=full_path) 
                except Exception as e:
                    self.api.speak(f"Error: {e}")
            elif os.access(full_path, os.X_OK):
                try:
                    if os.name == 'nt': os.startfile(full_path)
                    else: subprocess.Popen([full_path]) 
                    self.api.speak(f"Executed {item_name}.")
                except Exception as e:
                    self.api.speak(f"Could not execute: {e}")
            else:
                self.api.speak(f"Selected file: {item_name}")

    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_RETURN: self.on_open(None)
        elif key_code == wx.WXK_BACK:
            parent_dir = os.path.dirname(self.current_dir)
            if parent_dir != self.current_dir: self.go_to_path(parent_dir)
        event.Skip()

    def on_close(self, event=None):
        if self.frame: self.frame.Destroy()
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

    def run(self, file_path=None):
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
        button_sizer.AddStretchSpacer(1)
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
        
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.text_ctrl.SetValue(content)
                self.current_file_path = file_path
                self.frame.SetTitle(f"Text Editor - {os.path.basename(file_path)}")
                self.api.speak(f"Loaded file: {os.path.basename(file_path)}")
        except Exception as e:
            self.api.speak(f"Error loading file: {e}")

    def on_open(self, event):
        dialog = wx.FileDialog(self.frame, "Open Text File", wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            self.load_file(dialog.GetPath())
        dialog.Destroy()

    def on_save(self, event):
        if self.current_file_path:
            try:
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_ctrl.GetValue())
                self.api.speak(f"File saved: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                self.api.speak(f"Error saving file: {e}")
        else:
            self.on_save_as(event)

    def on_save_as(self, event):
        dialog = wx.FileDialog(self.frame, "Save Text File As", wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dialog.ShowModal() == wx.ID_OK:
            self.current_file_path = dialog.GetPath()
            try:
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_ctrl.GetValue())
                self.frame.SetTitle(f"Text Editor - {os.path.basename(self.current_file_path)}")
                self.api.speak(f"File saved as: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                self.api.speak(f"Error saving file: {e}")
        dialog.Destroy()

    def on_close(self, event=None):
        if self.frame: self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
