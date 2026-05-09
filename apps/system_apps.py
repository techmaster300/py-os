import wx
from api import BlindApp

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
        self.description = "Browse your virtual files."
        self.help_text = "Use arrow keys to browse files, and Enter to hear the name again."
        self.docs = "File Explorer connects to the Virtual File System. You can see files created via Terminal."

    def run(self):
        self.frame = wx.Frame(None, title="File Explorer", size=(500, 400))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        self.refresh_files()
        
        self.list.Bind(wx.EVT_LISTBOX, self.on_select)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("File Explorer opened.")

    def refresh_files(self):
        vfs = self.api.get_vfs()
        response = vfs.execute("list")
        items = response.replace("Directory contains ", "").split(": ")[-1].split(", ")
        self.list.Set(items)

    def on_select(self, event):
        item = self.list.GetStringSelection()
        self.api.speak(item)

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
