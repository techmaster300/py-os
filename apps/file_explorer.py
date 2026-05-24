import wx
import os
from api import BlindApp

class FileExplorerApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "File Explorer"
        self.description = "Browse your files."
        self.help_text = "Use Arrow keys to navigate, Enter to open, Backspace to go up, Alt+Left to go back."
        self.docs = "File Explorer lets you browse the VFS and host file system."
        self.vfs_root = os.path.abspath(os.path.join(os.getcwd(), "vfs"))
        self.current_dir = self.vfs_root
        self.history = []
        self.items = []

    def run(self, path=None):
        if path:
            self.current_dir = os.path.abspath(path)
        else:
            self.current_dir = self.vfs_root

        disp = self._display_path(self.current_dir)
        self._create_frame(f"File Explorer - {disp}", (700, 500))
        panel = self.make_panel(self.frame, "File Explorer Panel")
        main_sizer = self.vbox()

        nav_sizer = self.hbox()
        self.back_button = self.make_button(panel, "Back", self.go_back, "Back")
        self.back_button.Disable()
        self.up_button = self.make_button(panel, "Up", self.go_up, "Up")
        self.address_bar = self.make_textctrl(panel, name="Address Bar", style=wx.TE_PROCESS_ENTER)
        self.address_bar.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.address_bar.SetForegroundColour(wx.Colour(255, 255, 255))

        nav_sizer.Add(self.back_button, 0, wx.ALL, 5)
        nav_sizer.Add(self.up_button, 0, wx.ALL, 5)
        nav_sizer.Add(self.address_bar, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(nav_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.list = self.make_listctrl(panel, "File List", style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(255, 255, 255))
        self.list.InsertColumn(0, "Name", width=400)
        self.list.InsertColumn(1, "Type", width=100)
        main_sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = self.hbox()
        self.refresh_btn = self.make_button(panel, "Refresh", self.on_refresh, "Refresh")
        btn_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer(1)
        self.close_btn = self.make_button(panel, "Close", self.on_close, "Close")
        btn_sizer.Add(self.close_btn, 0, wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)

        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.address_bar.Bind(wx.EVT_TEXT_ENTER, self.go_to_address)

        self.refresh_files()
        self.api.speak("File Explorer opened.")
        self._show_app(self.list)

    def _display_path(self, path):
        if path.startswith(self.vfs_root):
            rel = path[len(self.vfs_root):].replace("\\", "/")
            return f"/vfs{rel}" if rel else "/vfs"
        return path

    def refresh_files(self):
        self.list.DeleteAllItems()
        self.items = []
        try:
            raw = os.listdir(self.current_dir)
            raw.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            for i, name in enumerate(raw):
                full = os.path.join(self.current_dir, name)
                is_dir = os.path.isdir(full)
                self.list.InsertItem(i, name)
                self.list.SetItem(i, 1, "Folder" if is_dir else "File")
                self.items.append((name, is_dir))
            self.address_bar.SetValue(self._display_path(self.current_dir))
            self.frame.SetTitle(f"File Explorer - {self._display_path(self.current_dir)}")
            self.back_button.Enable(len(self.history) > 0)
            count = len(self.items)
            self.api.speak(f"{count} item{'s' if count != 1 else ''}.", interrupt=False)
        except Exception as e:
            self.api.speak(f"Error: {e}")

    def go_to_path(self, path):
        if os.path.isdir(path):
            self.history.append(self.current_dir)
            self.current_dir = os.path.abspath(path)
            self.refresh_files()
            if self.items:
                self.list.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            self.api.speak(f"Entered {os.path.basename(self.current_dir) or self.current_dir}")

    def go_back(self, event=None):
        if self.history:
            self.current_dir = self.history.pop()
            self.refresh_files()
            self.api.speak(f"Back to {os.path.basename(self.current_dir) or self.current_dir}")

    def go_up(self, event=None):
        parent = os.path.dirname(self.current_dir)
        if parent != self.current_dir:
            self.go_to_path(parent)

    def go_to_address(self, event):
        raw = self.address_bar.GetValue()
        if raw.startswith("/vfs"):
            raw = raw[4:] or "/"
        path = self.vfs_root + raw.replace("/", "\\")
        if os.path.isdir(path):
            self.go_to_path(path)
        else:
            self.api.speak("Invalid path.")

    def on_item_activated(self, event):
        idx = event.GetIndex()
        name, is_dir = self.items[idx]
        full = os.path.join(self.current_dir, name)
        if is_dir:
            self.go_to_path(full)
            return
        self.api.speak(f"Opening {name}", interrupt=False)
        lower = name.lower()
        if lower.endswith((".txt", ".md", ".log", ".json", ".py", ".csv")):
            self.api.launch_app("TextEditorApp", filepath=self._vfs_path(full) or full)
        elif lower.endswith((".wav", ".mp3", ".ogg", ".flac")):
            self.api.launch_app("AudioRecorderApp", file_path=full)
        else:
            try:
                os.startfile(full)
            except Exception as e:
                self.api.speak(f"Could not open file: {e}")

    def _vfs_path(self, real_path):
        if real_path.startswith(self.vfs_root):
            rel = real_path[len(self.vfs_root):].replace("\\", "/")
            return rel if rel else None
        return None

    def on_key_down(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_BACK:
            self.go_up()
        elif key == wx.WXK_LEFT and event.AltDown():
            self.go_back()
        else:
            event.Skip()

    def on_refresh(self, event=None):
        self.refresh_files()
        self.api.speak("Refreshed.")

    def on_close(self, event=None):
        if self.frame:
            self.frame.Destroy()
        self.api.sounds.play("close")
        self.api.desktop.on_app_closed(self)
