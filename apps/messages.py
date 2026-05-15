import wx
import socket
from api import BlindApp

class MessagesApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Messages"
        self.description = "Send and receive text messages over the network."
        self.help_text = "Tab to navigate. Enter IP address in 'To' field, type message in 'Message' field, and press Enter or Click Send."
        self.docs = "This app uses the system-wide Message Service on port 3030. Messages are announced even when this app is closed."

    def run(self):
        self.frame = wx.Frame(None, title="Messages", size=(500, 600))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # --- Recipient Config ---
        target_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, label="To IP Address:")
        lbl.SetForegroundColour(wx.Colour(255, 255, 255))
        self.ip_input = wx.TextCtrl(panel, value="127.0.0.1")
        self.ip_input.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.ip_input.SetForegroundColour(wx.Colour(255, 255, 255))
        self.ip_input.SetHelpText("Enter the IP address of the recipient.")
        
        target_sizer.Add(lbl, 0, wx.ALL | wx.CENTER, 5)
        target_sizer.Add(self.ip_input, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(target_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # --- Message History ---
        history_lbl = wx.StaticText(panel, label="Message History:")
        history_lbl.SetForegroundColour(wx.Colour(200, 200, 200))
        main_sizer.Add(history_lbl, 0, wx.LEFT | wx.TOP, 10)

        self.msg_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self.msg_list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.msg_list.SetForegroundColour(wx.Colour(0, 255, 0))
        self.msg_list.SetHelpText("List of sent and received messages.")
        main_sizer.Add(self.msg_list, 1, wx.EXPAND | wx.ALL, 10)
        
        # --- Send Box ---
        msg_lbl = wx.StaticText(panel, label="Type Message:")
        msg_lbl.SetForegroundColour(wx.Colour(200, 200, 200))
        main_sizer.Add(msg_lbl, 0, wx.LEFT, 10)

        self.send_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.send_input.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.send_input.SetForegroundColour(wx.Colour(255, 255, 255))
        self.send_input.SetHelpText("Type your message here and press Enter to send.")
        main_sizer.Add(self.send_input, 0, wx.EXPAND | wx.ALL, 10)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.send_btn = wx.Button(panel, label="Send Message")
        btn_sizer.Add(self.send_btn, 1, wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        panel.SetSizer(main_sizer)
        
        # Bindings
        self.send_input.Bind(wx.EVT_TEXT_ENTER, self.on_send)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_send)
        self.msg_list.Bind(wx.EVT_LISTBOX, self.on_item_focused)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        # Load history and subscribe
        for msg in self.api.message_service.history:
            self.msg_list.Append(msg)
        
        self.api.message_service.subscribe(self.add_message)
        
        self.frame.Show()
        self.api.speak("Messages app opened. All incoming messages will be announced.")
        self.send_input.SetFocus()

    def add_message(self, text):
        if self.msg_list:
            self.msg_list.Append(text)
            self.msg_list.SetSelection(self.msg_list.GetCount() - 1)

    def on_send(self, event):
        target_ip = self.ip_input.GetValue().strip()
        message = self.send_input.GetValue().strip()
        
        if not message:
            return
            
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.sendto(message.encode('utf-8'), (target_ip, self.api.message_service.port))
            formatted = f"To {target_ip}: {message}"
            self.api.message_service.history.append(formatted)
            self.add_message(formatted)
            self.api.speak(f"Message sent to {target_ip}")
            self.send_input.Clear()
        except Exception as e:
            self.api.speak(f"Failed to send: {e}")

    def on_item_focused(self, event):
        item = self.msg_list.GetStringSelection()
        self.api.speak(item)

    def on_close(self, event=None):
        self.api.message_service.unsubscribe(self.add_message)
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
