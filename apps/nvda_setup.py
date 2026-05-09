import wx
import os
import ctypes
from api import BlindApp

class NVDASetupApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "NVDA Setup Guide"
        self.description = "Instructions for enabling direct NVDA integration."
        self.api = api

    def run(self):
        self.frame = wx.Frame(None, title="NVDA Integration Guide", size=(600, 450))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        title = wx.StaticText(panel, label="How to Enable Direct NVDA Support")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 20)
        
        self.instructions = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.instructions.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.instructions.SetForegroundColour(wx.Colour(255, 255, 255))
        self.instructions.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        
        text = (
            "Step 1: Open your web browser.\n"
            "Step 2: Go to the official NVDA GitHub extras page.\n"
            "Step 3: Download 'nvdaControllerClient64.dll' if you are using 64-bit Python, "
            "or the 32-bit version otherwise.\n"
            "Step 4: Copy the downloaded DLL file.\n"
            "Step 5: Paste it directly into the BlindOS folder (where desktop.py is located).\n"
            "Step 6: Restart BlindOS.\n\n"
            "Once the DLL is detected, BlindOS will talk directly to NVDA, "
            "providing a much faster and more integrated experience."
        )
        self.instructions.SetValue(text)
        sizer.Add(self.instructions, 1, wx.EXPAND | wx.ALL, 20)
        
        # Check current status
        dll_name = "nvdaControllerClient64.dll" if ctypes.sizeof(ctypes.c_void_p) == 8 else "nvdaControllerClient32.dll"
        if os.path.exists(os.path.join(os.getcwd(), dll_name)):
            status_msg = "Status: NVDA Controller DLL is already installed! You are all set."
        else:
            status_msg = f"Status: {dll_name} not found in the current folder."
            
        status_label = wx.StaticText(panel, label=status_msg)
        status_label.SetForegroundColour(wx.Colour(0, 255, 0) if "installed" in status_msg else wx.Colour(255, 100, 100))
        sizer.Add(status_label, 0, wx.ALL | wx.CENTER, 10)
        
        close_btn = wx.Button(panel, label="Close Guide")
        sizer.Add(close_btn, 0, wx.ALL | wx.CENTER, 10)
        
        panel.SetSizer(sizer)
        
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        
        # Speak instructions
        full_speech = "NVDA Integration Guide opened. " + text + " " + status_msg
        self.api.speak(full_speech)
