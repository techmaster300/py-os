import wx
import datetime
from api import BlindApp

class ClockApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Clock"
        self.description = "Check the current time and date."
        self.help_text = "The current time and date will be announced automatically."
        self.docs = "Clock provides the current system time and date information."

    def run(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        msg = f"It is currently {time_str} on {date_str}."

        self._create_frame("Clock", (300, 150))
        panel = self.make_panel(self.frame, "Clock Panel")
        sizer = self.vbox()

        time_label = self.make_static(panel, time_str, "Time Display")
        time_label.SetFont(wx.Font(28, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        time_label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(time_label, 0, wx.ALL | wx.CENTER, 15)

        date_label = self.make_static(panel, date_str, "Date Display")
        date_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        date_label.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(date_label, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)
        self.api.speak(msg)
        self._show_app(time_label)
        wx.CallLater(3000, self.on_close)

    def on_close(self, event=None):
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
