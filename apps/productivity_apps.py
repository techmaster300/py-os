import wx
import json
import os
from api import BlindApp

class TimerApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Timer"
        self.description = "Set a countdown timer with presets and cancel."
        self.help_text = "Enter seconds or use preset buttons. Speak remaining or cancel."
        self.docs = "Timer speaks remaining every 10s and alerts when done."
        self.remaining = 0
        self.running = False
        self.cancelled = False
        self._tick_interval = 1000
        self._last_speak = 0

    def run(self):
        self._create_frame("Timer", (320, 300))
        panel = self.make_panel(self.frame)
        sizer = self.vbox()

        sizer.Add(self.make_static(panel, "Enter seconds:", "Seconds Label"), 0, wx.ALL | wx.CENTER, 5)

        self.input_ctrl = self.make_textctrl(panel, name="Seconds Input", style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        preset_sizer = self.hbox()
        for sec, label_text in [(30, "30s"), (60, "1m"), (300, "5m")]:
            preset_sizer.Add(self.make_button(panel, label_text, lambda evt, s=sec: self.on_preset(s), label_text), 1, wx.ALL, 3)
        sizer.Add(preset_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.status_label = self.make_static(panel, "Ready", "Status")
        self.status_label.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 5)

        btn_sizer = self.hbox()
        btn_sizer.Add(self.make_button(panel, "Start", self.on_start, "Start Timer"), 1, wx.ALL, 5)
        btn_sizer.Add(self.make_button(panel, "Cancel", self.on_cancel, "Cancel Timer"), 1, wx.ALL, 5)
        btn_sizer.Add(self.make_button(panel, "Speak Time", self.on_speak_remaining, "Speak Remaining Time"), 1, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        panel.SetSizer(sizer)
        self.api.speak("Timer opened.")
        self._show_app(self.input_ctrl)

    def on_preset(self, seconds):
        self.input_ctrl.SetValue(str(seconds))
        self.on_start(None)

    def on_start(self, event):
        val = self.input_ctrl.GetValue()
        try:
            seconds = int(val)
            if seconds <= 0:
                self.api.speak("Enter a positive number.")
                return
            self.remaining = seconds
            self.running = True
            self.cancelled = False
            self._last_speak = seconds
            self.status_label.SetLabel(f"Timer: {seconds}s")
            self.input_ctrl.Enable(False)
            self.api.speak(f"Timer started for {seconds} seconds.")
        except ValueError:
            self.api.speak("Enter a valid number.")

    def on_tick(self):
        if not self.running or self.cancelled:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            self.running = False
            self.api.play_sound("alert")
            self.api.speak("Timer finished!")
            self.status_label.SetLabel("Finished")
            self.input_ctrl.Enable(True)
        else:
            self.status_label.SetLabel(f"Timer: {self.remaining}s")
            if self.remaining % 10 == 0:
                self.api.speak(f"{self.remaining} seconds remaining", interrupt=False)

    def on_cancel(self, event):
        if self.running:
            self.cancelled = True
            self.running = False
            self.status_label.SetLabel("Cancelled")
            self.input_ctrl.Enable(True)
            self.api.speak("Timer cancelled.")
        else:
            self.api.speak("No timer running.")

    def on_speak_remaining(self, event):
        if self.running and self.remaining > 0:
            self.api.speak(f"{self.remaining} seconds remaining.")
        elif self.running:
            self.api.speak("Timer is finishing.")
        else:
            self.api.speak("No timer active.")

    def get_terminal_commands(self):
        return {"start <seconds>": "Start a timer for the specified seconds."}

    def terminal_input(self, command):
        parts = command.split()
        if len(parts) >= 2 and parts[0].lower() == "start":
            try:
                seconds = int(parts[1])
                self.input_ctrl.SetValue(str(seconds))
                self.on_start(None)
            except ValueError:
                self.api.terminal_output("Error: Please enter a valid number.")
        else:
            self.api.terminal_output("Commands: 'start <seconds>'")

class RemindersApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Reminders"
        self.description = "Save, edit, and prioritize reminders."
        self.help_text = "Type and press Enter to add. Delete to remove, F2 to edit. Priority: High/Medium/Low."
        self.docs = "Reminders persist between sessions. Each can have high, medium, or low priority."
        self.db_path = self.api.get_data_path("reminders.json")
        self.reminders = []
        self.priorities = {}
        self.due_dates = {}
        self.load_reminders()

    def load_reminders(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    data = json.load(f)
                    self.reminders = data.get("items", [])
                    self.priorities = data.get("priorities", {})
                    self.due_dates = data.get("due_dates", {})
            except Exception:
                self.reminders = []
        else:
            self.reminders = []

    def save_reminders(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump({
                    "items": self.reminders,
                    "priorities": self.priorities,
                    "due_dates": self.due_dates,
                }, f, indent=2)
        except IOError as e:
            print(f"Error saving reminders: {e}")

    def priority_prefix(self, idx):
        p = self.priorities.get(str(idx), "medium")
        return {"high": "[!] ", "medium": "[-] ", "low": "[.] "}.get(p, "")

    def display_text(self, idx):
        due = self.due_dates.get(str(idx), "")
        due_str = f" (due {due})" if due else ""
        return f"{self.priority_prefix(idx)}{self.reminders[idx]}{due_str}"

    def run(self):
        self._create_frame("Reminders", (450, 450))
        panel = self.make_panel(self.frame)
        sizer = self.vbox()

        self.input_ctrl = self.make_textctrl(panel, name="Reminder Input", style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        btn_sizer = self.hbox()
        btn_sizer.Add(self.make_button(panel, "Add", self.on_add, "Add Reminder"), 1, wx.ALL, 3)
        btn_sizer.Add(self.make_button(panel, "Edit", self.on_edit, "Edit Reminder"), 1, wx.ALL, 3)
        btn_sizer.Add(self.make_button(panel, "Priority", self.on_set_priority, "Set Priority"), 1, wx.ALL, 3)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.list = self.make_listbox(panel, name="Reminders List")
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)

        self.refresh_list()

        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_add)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_edit)
        self.list.Bind(wx.EVT_LISTBOX, self.on_select)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)
        self.api.speak(f"Reminders opened. {len(self.reminders)} saved.")
        self._show_app(self.input_ctrl)

    def refresh_list(self):
        self.list.Clear()
        for i in range(len(self.reminders)):
            self.list.Append(self.display_text(i))

    def on_add(self, event):
        text = self.input_ctrl.GetValue().strip()
        if text:
            idx = len(self.reminders)
            self.reminders.append(text)
            self.priorities[str(idx)] = "medium"
            self.save_reminders()
            self.refresh_list()
            self.input_ctrl.Clear()
            self.api.speak(f"Reminder added: {text}")

    def on_edit(self, event):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND:
            self.api.speak("Select a reminder first.")
            return
        new_text = self.prompt("Edit reminder:", default=self.reminders[idx], title="Edit")
        if new_text and new_text.strip():
            self.reminders[idx] = new_text.strip()
            self.save_reminders()
            self.refresh_list()
            self.api.speak("Reminder updated.")

    def on_set_priority(self, event):
        idx = self.list.GetSelection()
        if idx == wx.NOT_FOUND:
            self.api.speak("Select a reminder first.")
            return
        current = self.priorities.get(str(idx), "medium")
        levels = ["high", "medium", "low"]
        sel = self.choice("Set priority:", levels, title="Priority")
        if sel:
            self.priorities[str(idx)] = sel.lower()
            self.save_reminders()
            self.refresh_list()
            self.api.speak(f"Priority set to {sel}.")

    def on_select(self, event):
        idx = self.list.GetSelection()
        if idx != wx.NOT_FOUND:
            p = self.priorities.get(str(idx), "medium")
            due = self.due_dates.get(str(idx), "")
            due_extra = f", due {due}" if due else ""
            self.api.speak(f"{p} priority{due_extra}: {self.reminders[idx]}")

    def on_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            idx = self.list.GetSelection()
            if idx != wx.NOT_FOUND:
                if not self.confirm("Delete this reminder?"):
                    return
                self.reminders.pop(idx)
                self.priorities = {str(int(k) if int(k) < idx else int(k)-1 if int(k) > idx else k): v for k, v in self.priorities.items() if int(k) != idx}
                self.due_dates = {str(int(k) if int(k) < idx else int(k)-1 if int(k) > idx else k): v for k, v in self.due_dates.items() if int(k) != idx}
                self.save_reminders()
                self.refresh_list()
                self.api.speak("Deleted.")
        elif event.GetKeyCode() == wx.WXK_F2:
            self.on_edit(None)
        else:
            event.Skip()

    def get_terminal_commands(self):
        return {"add <text>": "Add a new reminder.", "list": "List reminders."}

    def terminal_input(self, command):
        parts = command.split(maxsplit=1)
        if not parts: return
        action = parts[0].lower()
        if action == "add":
            if len(parts) > 1:
                reminder = parts[1]
                idx = len(self.reminders)
                self.reminders.append(reminder)
                self.priorities[str(idx)] = "medium"
                self.save_reminders()
                self.refresh_list() if self.frame else None
                self.api.terminal_output(f"Reminder added: {reminder}")
                self.api.speak("Reminder added.")
            else:
                self.api.terminal_output("Specify: add <text>")
        elif action == "list":
            if not self.reminders:
                self.api.terminal_output("No reminders.")
            for i, r in enumerate(self.reminders):
                self.api.terminal_output(f"{i+1}: {self.display_text(i)}")
        else:
            self.api.terminal_output("Commands: add, list")
