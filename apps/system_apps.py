import wx
import os
import datetime
import subprocess
import speech
from api import BlindApp
import audio_devices

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False

class SettingsApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "System Settings"
        self.description = "Configure tts, audio devices, updates, and mor."
        self.help_text = "Use Tab to navigate controls, and Enter to save."
        self.docs = "Settings allows you to customize the OS behavior. Voice speed can be adjusted from 50 to 400. Configure audio input and output devices."
        self.device_config_path = self.api.get_data_path("device_config.json")
        self.input_entries = []
        self.output_entries = []

    def run(self):
        self.frame = wx.Frame(None, title="Settings", size=(500, 600))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(30, 30, 30))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="System Settings")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)
        
        # Voice Speed Section
        voice_label = wx.StaticText(panel, label="Voice Speed:")
        voice_label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(voice_label, 0, wx.ALL, 10)
        
        self.speed_slider = wx.Slider(panel, value=200, minValue=50, maxValue=400, style=wx.SL_HORIZONTAL)
        self.speed_slider.SetBackgroundColour(wx.Colour(40, 40, 40))
        sizer.Add(self.speed_slider, 0, wx.EXPAND | wx.ALL, 10)

        # Speech Engine Section
        speech_label = wx.StaticText(panel, label="Speech Engine:")
        speech_label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(speech_label, 0, wx.ALL, 10)

        self.speech_modes = [
            ("Auto (NVDA when available)", "auto"),
            ("NVDA", "nvda"),
            ("SAPI", "sapi"),
        ]
        self.speech_choice = wx.Choice(panel, choices=[m[0] for m in self.speech_modes])
        current_mode = getattr(self.api.engine, "get_mode", lambda: "auto")()
        idx = next((i for i, m in enumerate(self.speech_modes) if m[1] == current_mode), 0)
        self.speech_choice.SetSelection(idx)
        self.speech_choice.Bind(wx.EVT_CHOICE, self.on_speech_mode_change)
        sizer.Add(self.speech_choice, 0, wx.EXPAND | wx.ALL, 8)
        
        # Audio Devices Section
        if HAS_SOUNDDEVICE:
            devices_label = wx.StaticText(panel, label="Audio Devices:")
            devices_label.SetForegroundColour(wx.Colour(255, 255, 255))
            devices_label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            sizer.Add(devices_label, 0, wx.ALL, 10)
            
            # Input Device
            input_label = wx.StaticText(panel, label="Input Device (Microphone):")
            input_label.SetForegroundColour(wx.Colour(200, 200, 200))
            sizer.Add(input_label, 0, wx.ALL, 8)
            
            self.input_entries = self.get_input_devices()
            input_labels = [self._device_label(d) for d in self.input_entries] or ["Default"]
            self.input_choice = wx.Choice(panel, choices=input_labels)
            self.input_choice.SetBackgroundColour(wx.Colour(40, 40, 40))
            self.input_choice.SetForegroundColour(wx.Colour(255, 255, 255))
            
            # Load saved input device
            config = self.load_device_config()
            selected_input_index = audio_devices.resolve_selected_index(
                self.input_entries, config, "input_device_index", "input_device"
            )
            if selected_input_index is not None:
                for i, entry in enumerate(self.input_entries):
                    if entry["index"] == selected_input_index:
                        self.input_choice.SetSelection(i)
                        break
                else:
                    self.input_choice.SetSelection(0)
            else:
                self.input_choice.SetSelection(0)
            
            sizer.Add(self.input_choice, 0, wx.EXPAND | wx.ALL, 8)
            
            # Output Device
            output_label = wx.StaticText(panel, label="Output Device (Speaker):")
            output_label.SetForegroundColour(wx.Colour(200, 200, 200))
            sizer.Add(output_label, 0, wx.ALL, 8)
            
            self.output_entries = self.get_output_devices()
            output_labels = [self._device_label(d) for d in self.output_entries] or ["Default"]
            self.output_choice = wx.Choice(panel, choices=output_labels)
            self.output_choice.SetBackgroundColour(wx.Colour(40, 40, 40))
            self.output_choice.SetForegroundColour(wx.Colour(255, 255, 255))
            
            # Load saved output device
            selected_output_index = audio_devices.resolve_selected_index(
                self.output_entries, config, "output_device_index", "output_device"
            )
            if selected_output_index is not None:
                for i, entry in enumerate(self.output_entries):
                    if entry["index"] == selected_output_index:
                        self.output_choice.SetSelection(i)
                        break
                else:
                    self.output_choice.SetSelection(0)
            else:
                self.output_choice.SetSelection(0)
            
            sizer.Add(self.output_choice, 0, wx.EXPAND | wx.ALL, 8)
            
            # Test button
            test_btn = wx.Button(panel, label="Test Audio")
            test_btn.SetBackgroundColour(wx.Colour(50, 50, 100))
            test_btn.SetForegroundColour(wx.Colour(255, 255, 255))
            test_btn.Bind(wx.EVT_BUTTON, self.on_test_audio)
            sizer.Add(test_btn, 0, wx.EXPAND | wx.ALL, 8)

        # Sound Theme Section
        theme_label = wx.StaticText(panel, label="Sound Theme:")
        theme_label.SetForegroundColour(wx.Colour(255, 255, 255))
        theme_label.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(theme_label, 0, wx.ALL, 10)

        themes = self.api.sounds.get_available_themes()
        self.theme_choice = wx.Choice(panel, choices=themes if themes else ["Modern"])
        self.theme_choice.SetBackgroundColour(wx.Colour(40, 40, 40))
        self.theme_choice.SetForegroundColour(wx.Colour(255, 255, 255))
        current_theme = self.api.sounds.current_theme
        if current_theme in themes:
            self.theme_choice.SetSelection(themes.index(current_theme))
        else:
            self.theme_choice.SetSelection(0)
        self.theme_choice.Bind(wx.EVT_CHOICE, self.on_theme_preview)
        sizer.Add(self.theme_choice, 0, wx.EXPAND | wx.ALL, 8)

        # Update button
        update_btn = wx.Button(panel, label="Check for Updates")
        update_btn.SetBackgroundColour(wx.Colour(50, 50, 50))
        update_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        update_btn.Bind(wx.EVT_BUTTON, self.check_updates)
        sizer.Add(update_btn, 0, wx.EXPAND | wx.ALL, 10)

        # Save and Close button
        close_btn = wx.Button(panel, label="Save and Close")
        close_btn.SetBackgroundColour(wx.Colour(0, 100, 0))
        close_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        sizer.Add(close_btn, 0, wx.EXPAND | wx.ALL, 15)
        
        panel.SetSizer(sizer)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("Settings opened. Configure voice speed and audio devices.")

    def get_input_devices(self):
        """Get list of available input devices."""
        try:
            return audio_devices.list_input_devices()
        except Exception as e:
            print(f"Error querying input devices: {e}")
            return []

    def get_output_devices(self):
        """Get list of available output devices."""
        try:
            return audio_devices.list_output_devices()
        except Exception as e:
            print(f"Error querying output devices: {e}")
            return []

    def _device_label(self, device_entry):
        return f"{device_entry['name']}"

    def load_device_config(self):
        """Load device configuration from file."""
        return audio_devices.load_device_config(self.api.data_dir)

    def save_device_config(self, input_device, output_device):
        """Save device configuration to file."""
        try:
            audio_devices.save_device_config(self.api.data_dir, input_device, output_device)
        except Exception as e:
            print(f"Error saving device config: {e}")

    def on_test_audio(self, event):
        """Test audio output."""
        self.api.speak("Testing audio. You should hear a sound.")
        self.api.play_sound("startup")

    def on_theme_preview(self, event):
        theme_name = self.theme_choice.GetStringSelection()
        if theme_name:
            self.api.sounds.current_theme = theme_name
            self.api.play_sound("startup")
            self.api.speak(theme_name)

    def _apply_speech_mode_selection(self, announce=True):
        sel = self.speech_choice.GetSelection()
        if sel < 0 or sel >= len(self.speech_modes):
            return
        speech_mode = self.speech_modes[sel][1]
        mode_ok = getattr(self.api.engine, "set_mode", lambda _m: False)(speech_mode)
        if not announce:
            return
        if speech_mode == "nvda" and not getattr(self.api.engine, "use_nvda", False):
            self.api.speak("NVDA is not active, so speech is using SAPI until NVDA is available.", interrupt=False)
        elif mode_ok:
            spoken_name = "Auto" if speech_mode == "auto" else speech_mode.upper()
            self.api.speak(f"Speech mode switched to {spoken_name}.", interrupt=False)
        else:
            self.api.speak("Could not switch speech mode.", interrupt=False)

    def on_speech_mode_change(self, event):
        self._apply_speech_mode_selection(announce=True)

    def check_updates(self, event):
        self.api.speak("Checking for updates...")
        try:
            subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/wasilewsk/py-os.git"], check=True)
            result = subprocess.run(["git", "pull", "origin", "master"], capture_output=True, text=True, check=True)
            
            if "Already up to date" in result.stdout:
                self.api.speak("System is already up to date. Checking requirements...")
            else:
                self.api.speak("Core updates downloaded. Updating requirements...")
            
            # Re-install requirements
            subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
            self.cleanup_deprecated_sound_artifacts()
            self.api.speak("Update completed successfully. All dependencies are up to date.")
        except subprocess.CalledProcessError as e:
            self.api.speak(f"Update failed: {e.stderr if e.stderr else 'Check your internet connection or git status'}")
        except Exception as e:
            self.api.speak(f"Error during update: {e}")

    def cleanup_deprecated_sound_artifacts(self):
        """Clean stale/legacy sound-theme artifacts without resetting active settings."""
        candidates = [
            self.api.get_data_path("sound_theme_app_state.json"),
            self.api.get_data_path("theme_creator_draft.json"),
            self.api.get_data_path("theme_creator_step.tmp"),
        ]
        for path in candidates:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def on_close(self, event=None):
        """Save settings and close."""
        # Ensure speech selection is persisted even if user didn't change focus after selecting.
        self._apply_speech_mode_selection(announce=False)

        if HAS_SOUNDDEVICE:
            input_sel = self.input_choice.GetSelection()
            output_sel = self.output_choice.GetSelection()
            input_device = self.input_entries[input_sel] if 0 <= input_sel < len(self.input_entries) else {"index": None, "name": "Default"}
            output_device = self.output_entries[output_sel] if 0 <= output_sel < len(self.output_entries) else {"index": None, "name": "Default"}
            self.save_device_config(input_device, output_device)
            self.api.speak(
                f"Settings saved. Audio devices: input {input_device.get('name', 'Default')}, output {output_device.get('name', 'Default')}."
            )
        selected_theme = self.theme_choice.GetStringSelection()
        if selected_theme:
            self.api.sounds.save_theme_name(selected_theme)
            self.api.sounds.current_theme = selected_theme
        
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)

class FileExplorerApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "File Explorer"
        self.description = "Browse your files."
        self.help_text = "Use Arrow keys to navigate, Enter to open, and Backspace to go up."
        self.docs = "File Explorer allows you to browse the host file system."
        self.current_dir = os.getcwd()
        self.history = []
        self.items = []

    def run(self):
        self.frame = wx.Frame(None, title=f"File Explorer - {self.current_dir}", size=(700, 500))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Navigation Toolbar ---
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.back_button = wx.Button(panel, label="Back")
        self.up_button = wx.Button(panel, label="Up")
        self.address_bar = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.address_bar.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.address_bar.SetForegroundColour(wx.Colour(255, 255, 255))

        nav_sizer.Add(self.back_button, 0, wx.ALL, 5)
        nav_sizer.Add(self.up_button, 0, wx.ALL, 5)
        nav_sizer.Add(self.address_bar, 1, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(nav_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # --- File List ---
        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        self.list.InsertColumn(0, "Name", width=400)
        self.list.InsertColumn(1, "Type", width=100)
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
        self.up_button.Bind(wx.EVT_BUTTON, self.go_up)
        self.address_bar.Bind(wx.EVT_TEXT_ENTER, self.go_to_address)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        refresh_btn.Bind(wx.EVT_BUTTON, lambda e: self.refresh_files())
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.refresh_files()
        self.frame.Show()
        self.api.speak("File Explorer opened.")
        self.list.SetFocus()

    def refresh_files(self):
        self.list.DeleteAllItems()
        self.items = []
        try:
            raw_items = os.listdir(self.current_dir)
            # Sort: folders first, then files
            raw_items.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            
            for i, name in enumerate(raw_items):
                full_path = os.path.join(self.current_dir, name)
                is_dir = os.path.isdir(full_path)
                item_type = "Folder" if is_dir else "File"
                
                self.list.InsertItem(i, name)
                self.list.SetItem(i, 1, item_type)
                self.items.append((name, is_dir))
            
            self.address_bar.SetValue(self.current_dir)
            self.frame.SetTitle(f"File Explorer - {self.current_dir}")
            self.back_button.Enable(len(self.history) > 0)
        except Exception as e:
            self.api.speak(f"Error: {e}")

    def go_to_path(self, path):
        if os.path.isdir(path):
            self.history.append(self.current_dir)
            self.current_dir = os.path.abspath(path)
            self.refresh_files()
            if self.items:
                self.list.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            self.api.speak(f"Entered {os.path.basename(self.current_dir) or self.current_dir}")

    def go_back(self, event):
        if self.history:
            self.current_dir = self.history.pop()
            self.refresh_files()
            self.api.speak(f"Back to {os.path.basename(self.current_dir) or self.current_dir}")

    def go_up(self, event):
        parent = os.path.dirname(self.current_dir)
        if parent != self.current_dir:
            self.go_to_path(parent)

    def go_to_address(self, event):
        path = self.address_bar.GetValue()
        if os.path.isdir(path):
            self.go_to_path(path)
        else:
            self.api.speak("Invalid path.")

    def on_item_activated(self, event):
        index = event.GetIndex()
        name, is_dir = self.items[index]
        full_path = os.path.join(self.current_dir, name)
        
        if is_dir:
            self.go_to_path(full_path)
        else:
            self.api.speak(f"Opening {name}", interrupt=False)
            lower = name.lower()
            if lower.endswith((".txt", ".md", ".log", ".json", ".py", ".csv")):
                self.api.launch_app("TextEditorApp", file_path=full_path)
            elif lower.endswith((".wav", ".mp3", ".ogg", ".flac")):
                self.api.launch_app("AudioRecorderApp", file_path=full_path)
            else:
                try:
                    if os.name == 'nt': os.startfile(full_path)
                    else: subprocess.Popen(['xdg-open', full_path])
                except Exception as e:
                    self.api.speak(f"Could not open file: {e}")

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_BACK:
            self.go_up(None)
        elif keycode == wx.WXK_LEFT and event.AltDown():
            self.go_back(None)
        else:
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
            # Note: eval is dangerous in a real OS, but for a simulator it's okay for now.
            # Using a safe dict for eval.
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
        self.api.speak("Text Editor opened.", interrupt=False)
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
                self.api.speak(f"Loaded file: {os.path.basename(file_path)}", interrupt=False)
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
