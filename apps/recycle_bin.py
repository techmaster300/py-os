import wx
import os
import json
import shutil
from api import BlindApp

class RecycleBinApp(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "Recycle Bin"
        self.description = "View, restore, or permanently delete trashed files."
        self.help_text = "Tab to navigate list. Enter to select. Buttons below to restore or empty."
        self.frame = None
        self.list = None
        self.info = {}
        self.trash_dir = None

    def _get_trash_dir(self):
        vfs = getattr(self.api, 'kernel', None)
        if vfs and hasattr(vfs, '_trash_dir'):
            return vfs._trash_dir
        return os.path.join(os.getcwd(), "vfs", ".trash")

    def _get_trash_info_path(self):
        return os.path.join(self._get_trash_dir(), ".trash_info.json")

    def _load_info(self):
        path = self._get_trash_info_path()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _refresh_list(self):
        self.list.DeleteAllItems()
        self.info = self._load_info()
        trash_dir = self._get_trash_dir()
        items = sorted([f for f in os.listdir(trash_dir) if f != ".trash_info.json"])
        if not items:
            self.api.speak("Recycle Bin is empty.")
        for f in items:
            entry = self.info.get(f, {})
            orig = entry.get("original_path", "unknown")
            idx = self.list.GetItemCount()
            self.list.InsertItem(idx, f)
            self.list.SetItem(idx, 1, orig)
        self.list.SetColumnWidth(0, 250)
        self.list.SetColumnWidth(1, 350)

    def on_restore(self, event):
        sel = self.list.GetFirstSelected()
        if sel < 0:
            self.api.speak("No item selected.")
            return
        trash_name = self.list.GetItemText(sel)
        trash_dir = self._get_trash_dir()
        trash_path = os.path.join(trash_dir, trash_name)
        if not os.path.exists(trash_path):
            self.api.speak("File no longer exists in Recycle Bin.")
            self._refresh_list()
            return
        info = self._load_info()
        entry = info.get(trash_name, {})
        orig_rel = entry.get("original_path", trash_name)
        vfs_root = os.path.join(os.getcwd(), "vfs")
        restore_path = os.path.join(vfs_root, orig_rel)
        try:
            os.makedirs(os.path.dirname(restore_path), exist_ok=True)
            shutil.move(trash_path, restore_path)
            info.pop(trash_name, None)
            with open(self._get_trash_info_path(), "w") as f:
                json.dump(info, f, indent=2)
            self.api.speak(f"Restored {entry.get('original_name', trash_name)}.")
            self._refresh_list()
        except Exception as e:
            self.api.speak(f"Restore failed: {e}")

    def on_empty(self, event):
        if not self.confirm("Permanently delete all items in the Recycle Bin?", "Empty Recycle Bin"):
            return
        trash_dir = self._get_trash_dir()
        try:
            for item in os.listdir(trash_dir):
                item_path = os.path.join(trash_dir, item)
                if item == ".trash_info.json":
                    continue
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            with open(self._get_trash_info_path(), "w") as f:
                json.dump({}, f)
            self.api.speak("Recycle Bin emptied.")
            self._refresh_list()
        except Exception as e:
            self.api.speak(f"Empty failed: {e}")

    def on_close(self, event=None):
        super().on_close(event)

    def run(self, path=None):
        self.info = self._load_info()
        self._create_frame("Recycle Bin", (650, 450))
        panel = self.make_panel(self.frame, "Recycle Bin Panel")
        sizer = self.vbox()

        heading = wx.StaticText(panel, label="Recycle Bin")
        heading.SetName("Recycle Bin Heading")
        heading.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(heading, 0, wx.ALL | wx.CENTER, 10)

        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetName("Trash List")
        self.list.AppendColumn("Trash Name")
        self.list.AppendColumn("Original Location")
        self.list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.list.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = self.hbox()
        restore_btn = self.make_button(panel, "Restore Selected", self.on_restore, "Restore Selected")
        btn_sizer.Add(restore_btn, 1, wx.ALL, 5)
        empty_btn = self.make_button(panel, "Empty Recycle Bin", self.on_empty, "Empty Recycle Bin")
        btn_sizer.Add(empty_btn, 1, wx.ALL, 5)
        close_btn = self.make_button(panel, "Close", self.on_close, "Close")
        btn_sizer.Add(close_btn, 1, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND)

        panel.SetSizer(sizer)
        self._refresh_list()
        self._show_app(self.list)
