import wx
import threading
import requests
import json
import os
from api import BlindApp

CONV_FILE = "assistant_conversations.json"
SETTINGS_FILE = "assistant_settings.json"

class AssistantApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "AI Assistant"
        self.description = "Assistant powered by Ollama with conversation memory."
        self.help_text = "Type a question and press Enter. F2 or Settings button to configure."
        self.docs = "AI Assistant uses Ollama. Conversations persist between sessions."
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3"
        self.system_prompt = "You are a helpful assistant."
        self.conversation = []
        self.load_settings()
        self.load_conversation()

    def settings_path(self):
        return self.api.get_data_path(SETTINGS_FILE)

    def conv_path(self):
        return self.api.get_data_path(CONV_FILE)

    def load_settings(self):
        path = self.settings_path()
        if os.path.exists(path):
            try:
                data = json.load(open(path, "r"))
                self.ollama_url = data.get("url", self.ollama_url)
                self.model = data.get("model", self.model)
                self.system_prompt = data.get("system_prompt", self.system_prompt)
            except:
                pass

    def save_settings(self):
        with open(self.settings_path(), "w") as f:
            json.dump({
                "url": self.ollama_url,
                "model": self.model,
                "system_prompt": self.system_prompt,
            }, f, indent=2)

    def load_conversation(self):
        path = self.conv_path()
        if os.path.exists(path):
            try:
                self.conversation = json.load(open(path, "r"))
            except:
                self.conversation = []

    def save_conversation(self):
        with open(self.conv_path(), "w") as f:
            json.dump(self.conversation[-50:], f, indent=2)

    def run(self):
        self._create_frame('AI Assistant', size=(500, 350))
        panel = self.make_panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(20, 20, 50))
        sizer = self.vbox()

        top_sizer = self.hbox()
        self.status_label = wx.StaticText(panel, label="Type your question and press Enter")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.status_label.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        top_sizer.Add(self.status_label, 1, wx.ALL | wx.CENTER, 20)

        top_sizer.Add(self.make_button(panel, "Settings", self.on_settings, "Settings"), 0, wx.ALL, 10)
        top_sizer.Add(self.make_button(panel, "Clear", self.on_clear, "Clear"), 0, wx.ALL, 10)

        sizer.Add(top_sizer, 0, wx.EXPAND)

        self.input_ctrl = self.make_textctrl(panel, name="Question Input", style=wx.TE_PROCESS_ENTER)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 20)

        self.history = self.make_textctrl(panel, name="Conversation History", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.history.SetBackgroundColour(wx.Colour(10, 10, 30))
        self.history.SetForegroundColour(wx.Colour(200, 200, 255))
        sizer.Add(self.history, 1, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(sizer)
        self.input_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_ask)

        for entry in self.conversation:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            label = "You" if role == "user" else "AI"
            self.history.AppendText(f"{label}: {content}\n")

        self.api.speak("AI Assistant is ready.")
        self._show_app(self.input_ctrl)

    def on_settings(self, event):
        url = self.prompt("Ollama Server URL:", default=self.ollama_url, title="Settings")
        if url is None:
            return
        model = self.choice("Select model:", ["llama3", "llama3:70b", "mistral", "mixtral", "codellama", "phi3", "gemma", "qwen2.5"], title="Settings")
        if model is None:
            return
        sp = self.prompt("System prompt:", default=self.system_prompt, title="Settings")
        if sp is None:
            return
        self.ollama_url = url.strip() or self.ollama_url
        self.model = model
        self.system_prompt = sp.strip() or self.system_prompt
        self.save_settings()
        self.show_info("Settings saved.")

    def on_clear(self, event):
        if self.confirm("Clear all conversation history?", "Clear History"):
            self.conversation.clear()
            self.save_conversation()
            self.history.Clear()
            self.show_info("Conversation history cleared.")

    def on_ask(self, event):
        prompt = self.input_ctrl.GetValue().strip()
        self.input_ctrl.Clear()
        if not prompt:
            return
        self.conversation.append({"role": "user", "content": prompt})
        self.history.AppendText(f"You: {prompt}\n")
        self.status_label.SetLabel("Assistant is thinking...")
        self.api.speak("Thinking...")
        threading.Thread(target=self.call_ollama, args=(prompt,), daemon=True).start()

    def call_ollama(self, prompt):
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            for entry in self.conversation[-20:]:
                messages.append({"role": entry["role"], "content": entry["content"]})
            payload = {"model": self.model, "messages": messages, "stream": False}
            response = requests.post(
                self.ollama_url.replace("/generate", "/chat") if "/generate" in self.ollama_url else self.ollama_url + "/chat",
                json=payload, timeout=30
            )
            if response.status_code == 200:
                result = response.json().get("message", {}).get("content", "I couldn't generate a response.")
                wx.CallAfter(self.show_response, result)
            else:
                wx.CallAfter(self.show_response, f"Error {response.status_code}")
        except requests.ConnectionError:
            wx.CallAfter(self.show_response, "Connection Error. Is Ollama running?")
        except Exception:
            wx.CallAfter(self.show_response, "An unexpected error occurred.")

    def show_response(self, text):
        self.conversation.append({"role": "assistant", "content": text})
        self.save_conversation()
        self.status_label.SetLabel("Assistant is ready")
        self.history.AppendText(f"AI: {text}\n")
        self.api.speak(text)

    def on_close(self, event=None):
        self.save_conversation()
        super().on_close(event)
