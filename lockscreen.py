import wx
import hashlib
import json
import os
import config_manager

CONFIG_FILE = "lock_config.json"

def load_config(data_dir):
    path = os.path.join(data_dir, CONFIG_FILE)
    if os.path.exists(path):
        try:
            return json.load(open(path, "r"))
        except:
            pass
    return {"enabled": False, "lock_type": "pin", "hash": ""}

def save_config(data_dir, config):
    path = os.path.join(data_dir, CONFIG_FILE)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)

def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()

def check(value, config):
    return _hash(value) == config.get("hash", "")

class LockScreen(wx.Dialog):
    def __init__(self, parent, data_dir, sounds=None):
        super().__init__(parent, title="PyOS", style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        self.data_dir = data_dir
        self.config = load_config(data_dir)
        self.unlocked = False
        self.pin_buffer = ""
        self.sounds = sounds

        ac = config_manager.load_appearance_config(data_dir)
        lock_bg = ac.get("lockscreen_bg", "#000000")
        lock_title_c = ac.get("lockscreen_title_color", "#FFFFFF")
        lock_title_text = ac.get("lockscreen_title_text", "Lock Screen")
        lock_title_fs = ac.get("lockscreen_title_font_size", 18)
        lock_mode_c = ac.get("lockscreen_mode_color", "#B4B4B4")
        lock_status_c = ac.get("lockscreen_status_color", "#FF5050")
        lock_input_bg = ac.get("lockscreen_input_bg", "#1E1E1E")
        lock_input_fg = ac.get("lockscreen_input_fg", "#FFFFFF")
        lock_disp_fs = ac.get("lockscreen_display_font_size", 20)
        lock_input_fs = ac.get("lockscreen_input_font_size", 14)
        lock_pin_fs = ac.get("lockscreen_pin_font_size", 14)
        lock_mask = ac.get("lockscreen_mask_char", "*")
        lock_w = ac.get("lockscreen_width", 350)
        lock_h = ac.get("lockscreen_height", 460)

        self.SetSize(lock_w, lock_h)
        self.Center()
        self.SetBackgroundColour(wx.Colour(lock_bg))

        panel = wx.Panel(self)
        panel.SetName("Lock Screen Panel")
        panel.SetBackgroundColour(wx.Colour(lock_bg))
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(panel, label=lock_title_text)
        title.SetName("Lock Screen Title")
        title.SetForegroundColour(wx.Colour(lock_title_c))
        title.SetFont(wx.Font(lock_title_fs, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)

        self.display = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_CENTER)
        self.display.SetName("Lock Screen Display")
        self.display.SetBackgroundColour(wx.Colour(lock_input_bg))
        self.display.SetForegroundColour(wx.Colour(lock_input_fg))
        self.display.SetFont(wx.Font(lock_disp_fs, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.display, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        sizer.AddSpacer(10)

        self._lock_pin_fs = lock_pin_fs
        self._lock_input_fs = lock_input_fs
        self._lock_mask = lock_mask
        self.mode_label = wx.StaticText(panel, label=self._mode_display())
        self.mode_label.SetName("Lock Mode Label")
        self.mode_label.SetForegroundColour(wx.Colour(lock_mode_c))
        sizer.Add(self.mode_label, 0, wx.ALL | wx.CENTER, 5)

        self.status = wx.StaticText(panel, label="")
        self.status.SetName("Lock Status")
        self.status.SetForegroundColour(wx.Colour(lock_status_c))
        sizer.Add(self.status, 0, wx.ALL | wx.CENTER, 5)

        if self.config.get("lock_type") == "pin":
            sizer.Add(self._build_pin_pad(panel), 0, wx.ALL | wx.CENTER, 10)
        else:
            pwd_sizer = wx.BoxSizer(wx.VERTICAL)
            self.pwd_input = wx.TextCtrl(panel, style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
            self.pwd_input.SetName("Password Input")
            self.pwd_input.SetBackgroundColour(wx.Colour(lock_input_bg))
            self.pwd_input.SetForegroundColour(wx.Colour(lock_input_fg))
            self.pwd_input.SetFont(wx.Font(lock_input_fs, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            self.pwd_input.Bind(wx.EVT_TEXT_ENTER, self.on_unlock)
            pwd_sizer.Add(self.pwd_input, 0, wx.EXPAND | wx.ALL, 10)
            sizer.Add(pwd_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)

        unlock_btn = wx.Button(panel, label="Unlock")
        unlock_btn.SetName("Unlock Button")
        unlock_btn.Bind(wx.EVT_BUTTON, self.on_unlock)
        sizer.Add(unlock_btn, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.display.SetFocus()

    def _mode_display(self):
        t = self.config.get("lock_type", "pin")
        return f"Enter {t.upper()}" if t == "pin" else "Enter Password"

    def _build_pin_pad(self, panel):
        grid = wx.GridSizer(4, 3, 5, 5)
        keys = [
            ("1", "1"), ("2", "2"), ("3", "3"),
            ("4", "4"), ("5", "5"), ("6", "6"),
            ("7", "7"), ("8", "8"), ("9", "9"),
            ("", ""), ("0", "0"), ("⌫", "bs"),
        ]
        pin_fs = getattr(self, '_lock_pin_fs', 14)
        for label, action in keys:
            btn = wx.Button(panel, label=label, size=(70, 50))
            btn.SetName(label if label else "Backspace")
            btn.SetFont(wx.Font(pin_fs, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
            if action == "bs":
                btn.Bind(wx.EVT_BUTTON, self.on_backspace)
            elif action:
                btn.Bind(wx.EVT_BUTTON, lambda evt, d=action: self.on_digit(d))
            grid.Add(btn, 0, wx.EXPAND)
        return grid

    def on_digit(self, digit):
        self.pin_buffer += digit
        mask = getattr(self, '_lock_mask', "*")
        self.display.SetValue(mask * len(self.pin_buffer))
        self.status.SetLabel("")

    def on_backspace(self, event):
        if self.pin_buffer:
            self.pin_buffer = self.pin_buffer[:-1]
            mask = getattr(self, '_lock_mask', "*")
            self.display.SetValue(mask * len(self.pin_buffer))

    def on_unlock(self, event=None):
        if self.config.get("lock_type") == "pin":
            value = self.pin_buffer
        else:
            value = self.pwd_input.GetValue()

        if check(value, self.config):
            self.unlocked = True
            if self.sounds:
                self.sounds.play("logon")
            self.Close()
        else:
            self.status.SetLabel("Incorrect. Try again.")
            self.pin_buffer = ""
            self.display.SetValue("")
            if self.config.get("lock_type") != "pin":
                self.pwd_input.SetValue("")

    def on_close(self, event=None):
        if not self.unlocked:
            self.Hide()
            wx.MessageBox("You must unlock the system to continue.", "Locked", wx.OK | wx.ICON_WARNING)
            self.Show()
            return
        self.Destroy()
