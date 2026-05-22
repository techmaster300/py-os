import wx
import os
from api import BlindApp

class TextEditorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Text Editor"
        self.description = "Create and edit text files."
        self.help_text = "Type text to edit. Ctrl+S to save, Ctrl+O to open, Esc to exit."
        self.docs = "A simple text editor that saves files to your PyOS data directory."
        self.filepath = None

    def run(self, filepath=None):
        self.frame = wx.Frame(None, title="Text Editor", size=(600, 400))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        self.text_ctrl.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.text_ctrl.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)
        
        # Accelerators
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('S'), 101),
            (wx.ACCEL_CTRL, ord('O'), 102),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, 103)
        ])
        self.frame.SetAcceleratorTable(accel_tbl)
        self.frame.Bind(wx.EVT_MENU, self.on_save, id=101)
        self.frame.Bind(wx.EVT_MENU, self.on_open, id=102)
        self.frame.Bind(wx.EVT_MENU, self.on_close, id=103)
        
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        
        if filepath:
            self.filepath = filepath
            try:
                real_path = self.api.get_vfs().get_real_path(filepath)
                if os.path.exists(real_path) and os.path.isfile(real_path):
                    with open(real_path, "r") as f:
                        self.text_ctrl.SetValue(f.read())
                    self.api.speak(f"Text Editor opened, loaded {filepath}.")
                else:
                    self.api.speak(f"Text Editor opened. File {filepath} not found.")
            except Exception as e:
                self.api.speak(f"Text Editor opened, but failed to load {filepath}: {e}")
        else:
            self.api.speak("Text Editor opened.")
        
        self.text_ctrl.SetFocus()

    def on_save(self, event=None):
        if not self.filepath:
            dlg = wx.TextEntryDialog(self.frame, "Enter filename to save (in VFS):", "Save File")
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetValue()
                if filename:
                    self.filepath = filename
            dlg.Destroy()
        
        if self.filepath:
            try:
                real_path = self.api.get_vfs().get_real_path(self.filepath)
                os.makedirs(os.path.dirname(real_path), exist_ok=True)
                with open(real_path, "w") as f:
                    f.write(self.text_ctrl.GetValue())
                
                msg = f"File {self.filepath} saved to virtual file system."
                self.api.speak(msg)
                self.api.terminal_output(f"[Editor] {msg}")
            except Exception as e:
                self.api.speak(f"Failed to save file: {e}")

    def get_terminal_commands(self):
        return {
            "save <filename>": "Save current content to VFS.",
            "open <filename>": "Open file from VFS."
        }

    def terminal_input(self, command):
        parts = command.split(maxsplit=1)
        if not parts: return
        action = parts[0].lower()
        
        if action == "save":
            if len(parts) > 1:
                self.filepath = parts[1]
            self.on_save(None)
        elif action == "open":
            if len(parts) > 1:
                self.filepath = parts[1]
                # Trigger internal open logic if file exists
                real_path = self.api.get_vfs().get_real_path(self.filepath)
                if os.path.exists(real_path):
                    with open(real_path, "r") as f:
                        self.text_ctrl.SetValue(f.read())
                    self.api.speak(f"Loaded {self.filepath}.")
                else:
                    self.api.terminal_output(f"File {self.filepath} not found.")
            else:
                self.api.terminal_output("Specify a filename: open <filename>")
        else:
            self.api.terminal_output("Unknown command. Available: save, open")
