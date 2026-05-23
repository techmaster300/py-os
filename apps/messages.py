import wx
import socket
import json
from datetime import datetime
from api import BlindApp

class MessagesApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Master-Chat"
        self.description = "Send and receive messages with timestamps."
        self.help_text = "Register or login with a username, then chat. Disconnect to log out."
        self.listening = False
        self.username = None
        self.logged_in = False
        self.all_messages = []
        self._tick_interval = 500

    def run(self):
        self._create_frame(title="Master-Chat", size=(500, 600))
        panel = wx.Panel(self.frame)
        sizer = wx.BoxSizer(wx.VERTICAL)

        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        filter_sizer.Add(wx.StaticText(panel, label="Filter by user:"), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.filter_input = wx.TextCtrl(panel)
        self.filter_input.SetHint("Username filter")
        self.filter_input.Bind(wx.EVT_TEXT, self.on_filter)
        filter_sizer.Add(self.filter_input, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(filter_sizer, 0, wx.EXPAND)

        auth_sizer = wx.BoxSizer(wx.VERTICAL)
        auth_sizer.Add(wx.StaticText(panel, label="Enter Username:"), 0, wx.ALL, 5)
        self.username_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.username_input.SetHint("Username")
        auth_sizer.Add(self.username_input, 1, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        reg_btn = wx.Button(panel, label="Register")
        reg_btn.Bind(wx.EVT_BUTTON, self.on_register)
        btn_sizer.Add(reg_btn, 0, wx.ALL, 5)

        login_btn = wx.Button(panel, label="Login")
        login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        btn_sizer.Add(login_btn, 0, wx.ALL, 5)

        disconnect_btn = wx.Button(panel, label="Disconnect")
        disconnect_btn.Bind(wx.EVT_BUTTON, self.on_logout)
        btn_sizer.Add(disconnect_btn, 0, wx.ALL, 5)
        auth_sizer.Add(btn_sizer, 0, wx.EXPAND)

        sizer.Add(auth_sizer, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(wx.StaticText(panel, label="Message History:"), 0, wx.LEFT, 10)
        self.msg_list = wx.ListBox(panel)
        sizer.Add(self.msg_list, 1, wx.EXPAND | wx.ALL, 10)

        sizer.Add(wx.StaticText(panel, label="Type Message:"), 0, wx.LEFT, 10)
        self.send_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.send_input.SetHint("Message")
        self.send_input.Disable()
        sizer.Add(self.send_input, 0, wx.EXPAND | wx.ALL, 10)
        self.send_input.Bind(wx.EVT_TEXT_ENTER, self.on_send)

        self.status_label = wx.StaticText(panel, label="Not connected")
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.sock.setblocking(0)
        self.listening = True
        self.api.speak("Messaging app opened. Register or login.")
        self._show_app(self.username_input)

    def timestamp(self):
        return datetime.now().strftime("%H:%M")

    def on_register(self, event):
        user = self.username_input.GetValue().strip()
        if not user:
            self.alert("Enter a username first.", "Input Required")
            return
        payload = json.dumps({"command": "create", "username": user})
        try:
            self.sock.sendto(payload.encode(), ('127.0.0.1', 3030))
            self.api.speak(f"Registering {user}...")
        except Exception:
            self.alert("Cannot reach server.", "Connection Error")

    def on_login(self, event):
        user = self.username_input.GetValue().strip()
        if not user:
            self.alert("Enter a username first.", "Input Required")
            return
        self.username = user
        payload = json.dumps({"command": "login", "username": user})
        try:
            self.sock.sendto(payload.encode(), ('127.0.0.1', 3030))
            self.send_input.Enable()
            self.logged_in = True
            self.status_label.SetLabel(f"Logged in as {user}")
            self.api.speak(f"Logged in as {user}")
        except Exception:
            self.alert("Cannot reach server.", "Connection Error")

    def on_logout(self, event):
        if self.logged_in:
            self.logged_in = False
            self.username = None
            self.send_input.Disable()
            self.status_label.SetLabel("Disconnected")
            self.api.speak("Disconnected.")
        else:
            self.api.speak("Not logged in.")

    def on_tick(self):
        if not self.listening:
            return
        try:
            data, _ = self.sock.recvfrom(1024)
            msg = json.loads(data.decode())
            ts = self.timestamp()
            formatted = f"[{ts}] {msg['user']}: {msg['text']}"
            self.add_message(formatted)
            self.api.speak(f"{msg['user']} says: {msg['text']}")
        except socket.error:
            pass
        except Exception:
            pass

    def add_message(self, text):
        self.all_messages.append(text)
        self._refresh_filter()

    def _refresh_filter(self):
        filter_text = self.filter_input.GetValue().strip().lower()
        self.msg_list.Clear()
        if not filter_text:
            for m in self.all_messages:
                self.msg_list.Append(m)
        else:
            for m in self.all_messages:
                if filter_text in m.lower():
                    self.msg_list.Append(m)
        if self.msg_list.GetCount() > 0:
            self.msg_list.SetSelection(self.msg_list.GetCount() - 1)

    def on_filter(self, event):
        self._refresh_filter()

    def on_send(self, event):
        if not self.logged_in:
            self.alert("Login first.", "Not Logged In")
            return
        text = self.send_input.GetValue().strip()
        if not text:
            return
        payload = json.dumps({"command": "message", "text": text})
        try:
            self.sock.sendto(payload.encode(), ('127.0.0.1', 3030))
            self.send_input.Clear()
        except Exception:
            self.alert("Failed to send. Check connection.", "Send Error")

    def on_close(self, event=None):
        self.listening = False
        self.logged_in = False
        try:
            self.sock.close()
        except Exception:
            pass
        super().on_close(event)
