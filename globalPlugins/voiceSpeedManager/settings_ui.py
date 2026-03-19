import wx
import os
from gui.settingsDialogs import SettingsPanel
from logHandler import log
from .config import conf

import synthDriverHandler

class VoiceSpeedSettingsPanel(SettingsPanel):
    title = "Voice Speed Manager"

    def makeSettings(self, settingsSizer):
        try:
            # Main Horizontal Sizer
            mainSizer = wx.BoxSizer(wx.HORIZONTAL)

            # --- Left Side: Applications ---
            appBox = wx.StaticBoxSizer(wx.StaticBox(self, label="Applications"), wx.VERTICAL)
            
            # App List
            self.appList = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            self.appList.InsertColumn(0, "Executable", width=150)
            self.appList.InsertColumn(1, "Path", width=200)
            self.appList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onAppSelected)
            self.appList.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onAppDeselected)
            appBox.Add(self.appList, 1, wx.EXPAND | wx.ALL, 5)

            # App Buttons
            appBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
            self.addAppBtn = wx.Button(self, label="Add App...")
            self.addAppBtn.Bind(wx.EVT_BUTTON, self.onAddApp)
            appBtnSizer.Add(self.addAppBtn, 0, wx.RIGHT, 5)

            self.removeAppBtn = wx.Button(self, label="Remove App")
            self.removeAppBtn.Bind(wx.EVT_BUTTON, self.onRemoveApp)
            self.removeAppBtn.Disable()
            appBtnSizer.Add(self.removeAppBtn, 0, wx.RIGHT, 5)

            appBox.Add(appBtnSizer, 0, wx.ALL, 5)
            mainSizer.Add(appBox, 1, wx.EXPAND | wx.ALL, 5)

            # --- Right Side: Language Profiles ---
            langBox = wx.StaticBoxSizer(wx.StaticBox(self, label="Language Profiles"), wx.VERTICAL)
            
            # Profile List
            self.profileList = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
            self.profileList.InsertColumn(0, "Language", width=100)
            self.profileList.InsertColumn(1, "Rate", width=80)
            self.profileList.InsertColumn(2, "Auto-Switch", width=100)
            langBox.Add(self.profileList, 1, wx.EXPAND | wx.ALL, 5)

            # Profile Buttons
            profileBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
            self.addProfileBtn = wx.Button(self, label="Add Profile...")
            self.addProfileBtn.Bind(wx.EVT_BUTTON, self.onAddProfile)
            self.addProfileBtn.Disable() # Disabled until app selected
            profileBtnSizer.Add(self.addProfileBtn, 0, wx.RIGHT, 5)

            self.removeProfileBtn = wx.Button(self, label="Remove Profile")
            self.removeProfileBtn.Bind(wx.EVT_BUTTON, self.onRemoveProfile)
            self.removeProfileBtn.Disable()
            profileBtnSizer.Add(self.removeProfileBtn, 0, wx.RIGHT, 5)

            langBox.Add(profileBtnSizer, 0, wx.ALL, 5)
            mainSizer.Add(langBox, 1, wx.EXPAND | wx.ALL, 5)

            settingsSizer.Add(mainSizer, 1, wx.EXPAND | wx.ALL, 5)

            # Initial Populate
            self.populateAppList()

        except Exception as e:
            log.error(f"VoiceSpeedManager: Error in makeSettings: {e}", exc_info=True)
            settingsSizer.Add(wx.StaticText(self, label=f"Error: {e}"), 0, wx.ALL, 10)

    def populateAppList(self):
        self.appList.DeleteAllItems()
        apps = conf.get_apps()
        for exe, data in apps.items():
            idx = self.appList.InsertItem(self.appList.GetItemCount(), exe)
            self.appList.SetItem(idx, 1, data.get("path", ""))

    def populateProfileList(self, exe_name):
        self.profileList.DeleteAllItems()
        profiles = conf.get_profiles(exe_name)
        for p in profiles:
            idx = self.profileList.InsertItem(self.profileList.GetItemCount(), p["language"])
            self.profileList.SetItem(idx, 1, str(p["rate"]))
            self.profileList.SetItem(idx, 2, "Yes" if p.get("auto_switch") else "No")

    def getSelectedApp(self):
        sel = self.appList.GetFirstSelected()
        if sel != -1:
            return self.appList.GetItemText(sel)
        return None

    def onAppSelected(self, event):
        exe_name = self.getSelectedApp()
        if exe_name:
            self.removeAppBtn.Enable()
            self.addProfileBtn.Enable()
            self.populateProfileList(exe_name)

    def onAppDeselected(self, event):
        self.removeAppBtn.Disable()
        self.addProfileBtn.Disable()
        self.removeProfileBtn.Disable()
        self.profileList.DeleteAllItems()

    def onAddApp(self, event):
        with wx.FileDialog(self, "Select Executable", wildcard="Executable files (*.exe)|*.exe",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            path = fileDialog.GetPath()
            exe_name = os.path.basename(path)
            if conf.add_app(exe_name, full_path=path):
                self.populateAppList()
            else:
                wx.MessageBox(f"Application '{exe_name}' is already configured.", "Error", wx.OK | wx.ICON_ERROR)

    def onRemoveApp(self, event):
        exe_name = self.getSelectedApp()
        if exe_name:
            if wx.MessageBox(f"Remove configuration for {exe_name}?", "Confirm", wx.YES_NO | wx.ICON_QUESTION) == wx.YES:
                conf.remove_app(exe_name)
                self.populateAppList()
                self.profileList.DeleteAllItems()
                self.removeAppBtn.Disable()
                self.addProfileBtn.Disable()

    def onAddProfile(self, event):
        exe_name = self.getSelectedApp()
        if not exe_name: return
        
        dlg = ProfileDialog(self, "Add Language Profile")
        if dlg.ShowModal() == wx.ID_OK:
            lang, rate, auto = dlg.GetValues()
            if lang and rate.isdigit():
                conf.add_profile(exe_name, lang, int(rate), auto)
                self.populateProfileList(exe_name)
        dlg.Destroy()

    def onRemoveProfile(self, event):
        exe_name = self.getSelectedApp()
        sel = self.profileList.GetFirstSelected()
        if exe_name and sel != -1:
            lang = self.profileList.GetItemText(sel)
            conf.remove_profile(exe_name, lang)
            self.populateProfileList(exe_name)

    def onSave(self):
        """
        Called when the user presses OK or Apply in the Settings Dialog.
        Currently, changes are saved immediately by the interactive buttons,
        but this method is required by the abstract base class.
        """
        pass


class ProfileDialog(wx.Dialog):
    def __init__(self, parent, title):
        super(ProfileDialog, self).__init__(parent, title=title)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Language Selection
        sizer.Add(wx.StaticText(self, label="Language:"), 0, wx.ALL, 5)
        
        # Get available languages from SynthDriver
        try:
            synth = synthDriverHandler.getSynth()
            self.languages = getattr(synth, "availableLanguages", [])
            # If availableLanguages is a list of objects, we might need to handle it. 
            # Usually it's a list of strings (codes).
            # Some synths like OneCore return objects, need to check string representation.
            self.lang_choices = [str(l) for l in self.languages]
            self.lang_choices.sort()
        except Exception:
            self.lang_choices = []

        if not self.lang_choices:
            # Fallback if no languages found or error
            self.langInput = wx.TextCtrl(self)
            self.use_choice = False
        else:
            self.langInput = wx.Choice(self, choices=self.lang_choices)
            if self.lang_choices:
                self.langInput.SetSelection(0)
            self.use_choice = True
            
        sizer.Add(self.langInput, 0, wx.EXPAND | wx.ALL, 5)
        
        # Rate
        sizer.Add(wx.StaticText(self, label="Rate (0-100):"), 0, wx.ALL, 5)
        self.rateInput = wx.TextCtrl(self)
        sizer.Add(self.rateInput, 0, wx.EXPAND | wx.ALL, 5)
        
        # Auto Switch
        self.autoSwitchCheck = wx.CheckBox(self, label="Auto-switch to this language on focus")
        sizer.Add(self.autoSwitchCheck, 0, wx.ALL, 10)
        
        btns = self.CreateButtonSizer(wx.ID_OK | wx.ID_CANCEL)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizerAndFit(sizer)
        self.Centre()

    def GetValues(self):
        if self.use_choice:
            lang = self.lang_choices[self.langInput.GetSelection()]
        else:
            lang = self.langInput.GetValue()
        return lang, self.rateInput.GetValue(), self.autoSwitchCheck.IsChecked()
