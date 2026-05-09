import wx
import threading
import requests
import json
from api import BlindApp

class AssistantApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "AI Assistant"
        self.description = "Voice-enabled assistant powered by Ollama."
        self.help_text = "Type a question and press Enter. The assistant will speak the answer."
        self.docs = "AI Assistant uses a local Ollama server (llama3 model) to provide intelligent responses."
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"

    def run(self):
        self.frame = wx.Frame(None, title='AI Assistant', size=(500, 300))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(20, 20, 50))
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.status_label = wx.StaticText(panel, label="Type your question and press Enter")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.status_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 20)
        self.input_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 20)
        self.history = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.history.SetBackgroundColour(wx.Colour(10, 10, 30))
        self.history.SetForegroundColour(wx.Colour(200, 200, 255))
        sizer.Add(self.history, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(sizer)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_ask)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        self.frame.Show()
        self.api.speak("AI Assistant is ready.")
        self.input_ctrl.SetFocus()

    def on_ask(self, event):
        prompt = self.input_ctrl.GetValue().strip()
        self.input_ctrl.Clear()
        if not prompt: return
        self.history.AppendText(f"You: {prompt}\n")
        self.status_label.SetLabel("Assistant is thinking...")
        self.api.speak("Thinking...")
        threading.Thread(target=self.call_ollama, args=(prompt,), daemon=True).start()

    def call_ollama(self, prompt):
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False}
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json().get("response", "I couldn't generate a response.")
                wx.CallAfter(self.show_response, result)
            else:
                wx.CallAfter(self.show_response, f"Error {response.status_code}")
        except Exception:
            wx.CallAfter(self.show_response, f"Connection Error. Make sure Ollama is running.")

    def show_response(self, text):
        self.status_label.SetLabel("Assistant is ready")
        self.history.AppendText(f"AI: {text}\n")
        self.api.speak(text)
