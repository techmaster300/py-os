import wx
from api import BlindApp

class TerminalApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Terminal"
        self.description = "Command-line interface to the system kernel."
        self.help_text = "Type OS commands like 'list', 'create', 'shutdown', 'reboot', or 'winshell' and press Enter."
        self.docs = "Terminal provides direct access to the Virtual OS Kernel. Use 'help' to see all commands."

    def run(self):
        self.frame = wx.Frame(None, title='Terminal', size=(600, 400))
        self.panel = wx.Panel(self.frame)
        self.panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.output_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH)
        self.output_text.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.output_text.SetForegroundColour(wx.Colour(255, 255, 255))
        self.output_text.SetFont(wx.Font(12, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.output_text, 1, wx.EXPAND | wx.ALL, 10)
        self.input_ctrl = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        self.input_ctrl.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.input_ctrl.SetForegroundColour(wx.Colour(0, 255, 0))
        self.input_ctrl.SetFont(wx.Font(14, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 10)
        self.panel.SetSizer(sizer)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        # Register callback for shell output
        self.api.get_vfs().output_callback = lambda text: wx.CallAfter(self.shell_log, text)
        
        self.frame.Show()
        self.log("PyOS Terminal started. Type 'help' for commands.")
        self.api.speak("Terminal opened.")
        self.input_ctrl.SetFocus()

    def log(self, text):
        if text:
            self.output_text.AppendText(text + "\n")
            self.output_text.ShowPosition(self.output_text.GetLastPosition())

    def shell_log(self, text):
        self.log(text)
        self.api.speak(text)

    def on_enter(self, event):
        cmd_str = self.input_ctrl.GetValue().strip()
        self.input_ctrl.Clear()
        if not cmd_str: return

        # If an app is active, it still gets first priority for terminal input
        if self.api.desktop.active_app and hasattr(self.api.desktop.active_app, 'terminal_input'):
            self.api.desktop.active_app.terminal_input(cmd_str)
            self.log(f"-> {self.api.desktop.active_app.name}: {cmd_str}")
            return

        if cmd_str.lower() == "exit":
            self.on_close()
            return
        
        parts = cmd_str.split()
        cmd = parts[0].lower()
        args = parts[1:]

        kernel = self.api.get_vfs()
        
        # Special handling for 'open' to launch Text Editor for files
        if cmd == "open" and args:
            file_name = args[0]
            real_path = kernel.get_real_path(file_name)
            if os.path.isfile(real_path):
                self.api.launch_app("TextEditorApp", filepath=file_name)
                return

        self.log(f"> {cmd_str}")
        response = kernel.execute(cmd_str)
        if response:
            self.log(response)
            self.api.speak(response)

    def on_close(self, event=None):
        # Clear callback on close
        self.api.get_vfs().output_callback = None
        super().on_close(event)
