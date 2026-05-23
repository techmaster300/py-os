import wx
import os
import json
from api import BlindApp
from network_service import NetworkService

INSTALLED_DB = "app_store_installed.json"

class AppStore(BlindApp):
    def __init__(self, api):
        super().__init__(api)
        self.name = "App Store"
        self.description = "Browse, search, and download add-ons."
        self.help_text = "Tab to browse, Enter to download. Type to filter list."
        self.network = NetworkService()
        self.apps = {}
        self.installed = self._load_installed()
        self.all_items = []

    def _load_installed(self):
        path = self.api.get_data_path(INSTALLED_DB)
        if os.path.exists(path):
            try:
                return json.load(open(path, "r"))
            except:
                pass
        return []

    def _save_installed(self):
        path = self.api.get_data_path(INSTALLED_DB)
        with open(path, "w") as f:
            json.dump(self.installed, f, indent=2)

    def run(self):
        self._create_frame("App Store", (500, 500))
        panel = self.make_panel(self.frame)
        sizer = self.vbox()

        sizer.Add(self.make_static(panel, "Search (type to filter):", "Search Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.search_input = self.make_textctrl(panel, name="Search Input")
        self.search_input.Bind(wx.EVT_TEXT, self.on_search)
        sizer.Add(self.search_input, 0, wx.EXPAND | wx.ALL, 10)

        self.listbox = self.make_listbox(panel, name="Apps List")
        self.listbox.Bind(wx.EVT_LISTBOX, self.on_select)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 10)

        self.desc_label = self.make_static(panel, "Description: ", "Description")
        sizer.Add(self.desc_label, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = self.hbox()
        btn_sizer.Add(self.make_button(panel, "Download", self.on_download, "Download"), 1, wx.ALL, 5)
        btn_sizer.Add(self.make_button(panel, "Refresh", self.on_refresh, "Refresh"), 1, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self.status_label = self.make_static(panel, "", "Status")
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(sizer)

        self.refresh_list()
        self.api.speak("App Store opened. Type to search, arrows to browse.")
        self._show_app(self.search_input)

    def on_search(self, event):
        self._update_display()

    def _update_display(self):
        query = self.search_input.GetValue().strip().lower()
        if query:
            self.all_items = [k for k in self.apps if query in k.lower()]
        else:
            self.all_items = list(self.apps.keys())
        display = []
        for name in self.all_items:
            tag = " [INSTALLED]" if name in self.installed else ""
            display.append(f"{name}{tag}")
        self.listbox.Set(display)

    def on_select(self, event):
        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND: return
        name = self.all_items[sel]
        info = self.apps[name]
        tag = " (installed)" if name in self.installed else ""
        desc = f"{info['description']} (v{info['version']}){tag}"
        self.desc_label.SetLabel(desc)
        self.api.speak(f"{name}. {info['description']}{tag}")

    def on_refresh(self, event):
        self.status_label.SetLabel("Refreshing...")
        self.refresh_list()

    def refresh_list(self):
        try:
            resp = self.network.send_request("list_apps")
            if "apps" in resp:
                self.apps = resp["apps"]
                self._update_display()
                self.status_label.SetLabel(f"{len(self.apps)} apps available.")
            elif "error" in resp:
                self.status_label.SetLabel(f"Server error: {resp['error']}")
                self.api.speak("Failed to fetch apps.")
            else:
                self.status_label.SetLabel("Unexpected response.")
                self.api.speak("Failed to fetch apps.")
        except Exception:
            self.status_label.SetLabel("Cannot reach server. Is it running?")
            self.api.speak("Cannot reach server.")

    def on_download(self, event):
        sel = self.listbox.GetSelection()
        if sel == wx.NOT_FOUND:
            self.api.speak("Select an app first.")
            return
        name = self.all_items[sel]
        if name in self.installed:
            if self.confirm(f"{name} is installed. Uninstall it?"):
                self.installed.remove(name)
                self._save_installed()
                self._update_display()
                self.status_label.SetLabel(f"Uninstalled {name}.")
                self.api.speak(f"Uninstalled {name}.")
            return

        if not self.confirm(f"Download {name}?"):
            return
        self.status_label.SetLabel(f"Downloading {name}...")
        try:
            resp = self.network.send_request("download_item", {"name": name})
            if resp.get("status") == "downloaded":
                self.installed.append(name)
                self._save_installed()
                self._update_display()
                self.status_label.SetLabel(f"Downloaded {name}.")
                self.api.speak(f"Downloaded {name}.")
            elif "error" in resp:
                self.show_error(f"Download failed: {resp['error']}")
                self.status_label.SetLabel(f"Failed: {resp['error']}")
            else:
                self.show_error("Download failed.")
                self.status_label.SetLabel("Download failed.")
        except Exception:
            self.show_error("Cannot reach server. Is it running?")
            self.status_label.SetLabel("Cannot reach server.")
