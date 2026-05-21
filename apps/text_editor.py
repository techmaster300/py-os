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

    def run(self):
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
        self.api.speak("Text Editor opened.")
        self.text_ctrl.SetFocus()

    def on_save(self, event):
        if not self.filepath:
            dlg = wx.FileDialog(self.frame, "Save File", wildcard="*.txt", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                self.filepath = dlg.GetPath()
            dlg.Destroy()
        if self.filepath:
            with open(self.filepath, "w") as f:
                f.write(self.text_ctrl.GetValue())
            self.api.speak("File saved.")

    def on_open(self, event):
        dlg = wx.FileDialog(self.frame, "Open File", wildcard="*.txt", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.filepath = dlg.GetPath()
            with open(self.filepath, "r") as f:
                self.text_ctrl.SetValue(f.read())
            self.api.speak(f"Loaded {os.path.basename(self.filepath)}.")
        dlg.Destroy()
