import wx
import os
from api import BlindApp

class TextEditorApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Text Editor"
        self.description = "Create and edit text files."
        self.help_text = "Ctrl+S save, Ctrl+O open, Ctrl+F find, Ctrl+R replace, Ctrl+W word count, Ctrl+N new, Ctrl+T readonly, Esc exit."
        self.docs = "A text editor that saves files to your PyOS data directory."
        self.filepath = None
        self.readonly = False

    def run(self, filepath=None):
        # Register accelerators
        a_id = 1000
        for key, handler in [
            (ord('S'), self.on_save), (ord('O'), self.on_open_prompt),
            (wx.WXK_ESCAPE, self.on_close), (ord('N'), self.on_clear),
            (ord('F'), self.on_find), (ord('R'), self.on_replace),
            (ord('W'), self.on_word_count), (ord('T'), self.on_toggle_readonly),
        ]:
            flags = wx.ACCEL_CTRL if key not in (wx.WXK_ESCAPE,) else wx.ACCEL_NORMAL
            self.bind_accelerator(flags, key, a_id, handler)
            a_id += 1

        self._create_frame("Text Editor", (600, 450))
        panel = self.make_panel(self.frame, "Editor Panel")
        sizer = self.vbox()

        self.text_ctrl = self.make_textctrl(panel, name="Editor Text", style=wx.TE_MULTILINE)
        self.text_ctrl.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.text_ctrl.SetForegroundColour(wx.Colour(255, 255, 255))
        self.text_ctrl.Bind(wx.EVT_KEY_UP, self.on_update_status)
        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        self.status_bar = self.make_static(panel, "No file open", "Status Bar")
        self.status_bar.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(self.status_bar, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)

        if filepath:
            self.filepath = filepath
            self.status_bar.SetLabel(f"File: {filepath}")
            try:
                real_path = self.api.get_vfs().get_real_path(filepath)
                if os.path.exists(real_path) and os.path.isfile(real_path):
                    with open(real_path, "r") as f:
                        self.text_ctrl.SetValue(f.read())
                    self.api.speak(f"Text Editor opened, loaded {filepath}.")
                else:
                    self.api.speak(f"Text Editor opened. File {filepath} not found.")
            except Exception as e:
                self.api.speak(f"Text Editor opened, but failed to load {filepath}: {e}")
        else:
            self.api.speak("Text Editor opened.")

        self._show_app(self.text_ctrl)

    def on_open(self, filepath=None):
        if filepath:
            self.run(filepath=filepath)

    def on_update_status(self, event=None):
        content = self.text_ctrl.GetValue()
        lines = content.count("\n") + 1
        words = len(content.split()) if content.strip() else 0
        chars = len(content)
        insert = self.text_ctrl.GetInsertionPoint()
        line = self.text_ctrl.GetNumberOfLines()
        col = insert - self.text_ctrl.XYToPosition(0, line - 1) if line > 0 else 0
        if line > 0:
            line_start = self.text_ctrl.XYToPosition(0, line - 1)
            col = insert - line_start + 1
        ro = " [RO]" if self.readonly else ""
        if self.filepath:
            self.status_bar.SetLabel(f"{self.filepath}{ro}  Ln {line}, Col {col}  {words}w {chars}c")
        else:
            self.status_bar.SetLabel(f"New file{ro}  Ln {line}, Col {col}  {words}w {chars}c")
        event.Skip() if event else None

    def on_open_prompt(self, event=None):
        filename = self.prompt("Enter filename to open (in VFS):", title="Open File")
        if filename:
            self.filepath = filename
            real_path = self.api.get_vfs().get_real_path(filename)
            if os.path.exists(real_path) and os.path.isfile(real_path):
                with open(real_path, "r") as f:
                    self.text_ctrl.SetValue(f.read())
                self.api.speak(f"Loaded {filename}.")
            else:
                self.api.speak(f"File {filename} not found.")
            self.on_update_status()

    def on_save(self, event=None):
        if not self.filepath:
            filename = self.prompt("Enter filename to save (in VFS):", title="Save File")
            if filename:
                self.filepath = filename
            else:
                return

        if self.filepath:
            try:
                real_path = self.api.get_vfs().get_real_path(self.filepath)
                os.makedirs(os.path.dirname(real_path), exist_ok=True)
                with open(real_path, "w") as f:
                    f.write(self.text_ctrl.GetValue())
                self.on_update_status()
                msg = f"File {self.filepath} saved."
                self.api.speak(msg)
                self.api.terminal_output(f"[Editor] {msg}")
            except Exception as e:
                self.api.speak(f"Failed to save file: {e}")

    def on_clear(self, event=None):
        self.text_ctrl.Clear()
        self.filepath = None
        self.readonly = False
        self.on_update_status()
        self.api.speak("Editor cleared.")

    def on_word_count(self, event=None):
        content = self.text_ctrl.GetValue()
        chars = len(content)
        words = len(content.split()) if content.strip() else 0
        lines = content.count("\n") + 1
        self.api.speak(f"{words} words, {chars} characters, {lines} lines.")

    def on_toggle_readonly(self, event=None):
        self.readonly = not self.readonly
        self.text_ctrl.SetEditable(not self.readonly)
        self.on_update_status()
        self.api.speak("Readonly mode." if self.readonly else "Editable mode.")

    def on_close(self, event=None):
        if self.text_ctrl.GetValue().strip() and not self.confirm("Discard unsaved changes?"):
            if event:
                event.Veto()
            return
        super().on_close(event)

    def on_find(self, event=None):
        text = self.prompt("Enter text to find:", title="Find")
        if text:
            content = self.text_ctrl.GetValue()
            idx = content.lower().find(text.lower())
            if idx != -1:
                self.text_ctrl.SetSelection(idx, idx + len(text))
                self.text_ctrl.SetFocus()
                self.api.speak(f"Found {text}.")
            else:
                self.api.speak(f"'{text}' not found.")

    def on_replace(self, event=None):
        find_text = self.prompt("Find what:", title="Replace")
        if not find_text:
            return
        replace_text = self.prompt("Replace with:", default="", title="Replace")
        if replace_text is None:
            return
        content = self.text_ctrl.GetValue()
        new_content = content.replace(find_text, replace_text)
        self.text_ctrl.SetValue(new_content)
        self.on_update_status()
        self.api.speak("Replaced all occurrences.")

    def terminal_input(self, command):
        parts = command.split(maxsplit=1)
        if not parts: return
        action = parts[0].lower()

        if action == "save":
            if len(parts) > 1:
                self.filepath = parts[1]
            self.on_save(None)
        elif action == "open":
            if len(parts) > 1:
                self.filepath = parts[1]
                real_path = self.api.get_vfs().get_real_path(self.filepath)
                if os.path.exists(real_path):
                    with open(real_path, "r") as f:
                        self.text_ctrl.SetValue(f.read())
                    self.api.speak(f"Loaded {self.filepath}.")
                else:
                    self.api.terminal_output(f"File {self.filepath} not found.")
            else:
                self.api.terminal_output("Specify a filename: open <filename>")
        elif action == "wc":
            self.on_word_count()
        else:
            self.api.terminal_output("Unknown command. Available: save, open, wc")
