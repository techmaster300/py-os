import wx
import os
from api import BlindApp

class TerminalApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Terminal"
        self.description = "Command-line interface to the system kernel."
        self.help_text = "Type commands and press Enter. Up/Down for history, Tab to complete, Ctrl+L to clear."
        self.docs = "Terminal provides direct access to the Virtual OS Kernel. Use 'help' to see all commands."
        self.history = []
        self.history_idx = -1
        self._tick_interval = 100
        self.font_size = 12
        self.known_commands = [
            "help", "list", "open", "create", "delete", "where", "time",
            "exit", "shutdown", "reboot", "winshell", "clear", "cls",
        ]

    def run(self):
        a_id = 2000
        self.bind_accelerator(wx.ACCEL_CTRL, ord('='), a_id, self.on_font_up); a_id += 1
        self.bind_accelerator(wx.ACCEL_CTRL, ord('-'), a_id, self.on_font_down); a_id += 1
        self.bind_accelerator(wx.ACCEL_CTRL, ord('0'), a_id, self.on_font_reset)

        self._create_frame('Terminal', (600, 400))
        self.panel = self.make_panel(self.frame, "Terminal Panel")
        sizer = self.vbox()

        self.output_text = self.make_textctrl(self.panel, name="Terminal Output", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH)
        self.output_text.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.output_text.SetForegroundColour(wx.Colour(255, 255, 255))
        self._apply_output_font()
        sizer.Add(self.output_text, 1, wx.EXPAND | wx.ALL, 10)

        self.input_ctrl = self.make_textctrl(self.panel, name="Command Input", style=wx.TE_PROCESS_ENTER)
        self.input_ctrl.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.input_ctrl.SetForegroundColour(wx.Colour(0, 255, 0))
        self._apply_output_font()
        self.input_ctrl.Bind(wx.EVT_KEY_DOWN, self.on_key)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 10)
        self.panel.SetSizer(sizer)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_enter)

        self.api.get_vfs().output_callback = lambda text: wx.CallAfter(self.shell_log, text)

        self.log("PyOS Terminal started. Type 'help' for commands.")
        self.api.speak("Terminal opened.")
        self._show_app(self.input_ctrl)

    def _apply_output_font(self):
        f = wx.Font(self.font_size, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.output_text.SetFont(f)
        if hasattr(self, 'input_ctrl'):
            self.input_ctrl.SetFont(f)

    def on_font_up(self, event=None):
        self.font_size = min(24, self.font_size + 2)
        self._apply_output_font()
        self.api.speak(f"Font size {self.font_size}")

    def on_font_down(self, event=None):
        self.font_size = max(8, self.font_size - 2)
        self._apply_output_font()
        self.api.speak(f"Font size {self.font_size}")

    def on_font_reset(self, event=None):
        self.font_size = 12
        self._apply_output_font()
        self.api.speak("Font size reset to 12")

    def on_tick(self):
        self.api.get_vfs().process_shell_output()

    def on_key(self, event):
        key = event.GetKeyCode()
        if event.ControlDown() and key in (ord('L'), ord('l')):
            self.output_text.Clear()
            self.api.speak("Screen cleared.")
        elif key == wx.WXK_UP:
            if self.history:
                self.history_idx = max(0, self.history_idx - 1)
                self.input_ctrl.SetValue(self.history[self.history_idx])
        elif key == wx.WXK_DOWN:
            if self.history:
                self.history_idx = min(len(self.history), self.history_idx + 1)
                if self.history_idx >= len(self.history):
                    self.history_idx = len(self.history)
                    self.input_ctrl.Clear()
                else:
                    self.input_ctrl.SetValue(self.history[self.history_idx])
        elif key == wx.WXK_TAB:
            self.do_tab_complete()
        else:
            event.Skip()

    def do_tab_complete(self):
        text = self.input_ctrl.GetValue().strip()
        if not text:
            return
        parts = text.split()
        if len(parts) == 1:
            matches = [c for c in self.known_commands if c.startswith(parts[0])]
            if len(matches) == 1:
                self.input_ctrl.SetValue(matches[0] + " ")
            elif len(matches) > 1:
                common = os.path.commonprefix(matches)
                if common and common != parts[0]:
                    self.input_ctrl.SetValue(common)

    def log(self, text):
        if text:
            self.output_text.AppendText(text + "\n")
            self.output_text.ShowPosition(self.output_text.GetLastPosition())

    def shell_log(self, text):
        self.log(text)
        self.api.speak(text)

    def on_enter(self, event):
        cmd_str = self.input_ctrl.GetValue().strip()
        if not cmd_str:
            self.input_ctrl.Clear()
            return

        if not self.history or self.history[-1] != cmd_str:
            self.history.append(cmd_str)
        self.history_idx = len(self.history)

        self.input_ctrl.Clear()

        if cmd_str.lower() in ("clear", "cls"):
            self.output_text.Clear()
            self.api.speak("Screen cleared.")
            return

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
        self.api.get_vfs().output_callback = None
        super().on_close(event)
