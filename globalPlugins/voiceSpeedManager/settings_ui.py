import wx
import gui
import addonHandler
from .config import conf
import synthDriverHandler
from logHandler import log

addonHandler.initTranslation()

# Safety fallback for translation function
if "_" not in globals():
    try:
        _ = wx.GetTranslation
    except NameError:
        def _(msg): return msg

class VoiceSpeedSettingsPanel(gui.SettingsPanel):
    title = _("Voice Speed Manager")

    def makeSettings(self, settingsSizer):
        # Section 1: Application Rules
        app_box = wx.StaticBoxSizer(wx.StaticBox(self, label=_("Application Rules")), wx.VERTICAL)
        
        # List of rules
        self.rules_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.rules_list.InsertColumn(0, _("Application (.exe)"), width=150)
        self.rules_list.InsertColumn(1, _("Language"), width=100)
        
        self.populate_rules_list()
        
        app_box.Add(self.rules_list, 1, wx.EXPAND | wx.ALL, 5)
        
        # Add/Edit buttons (simplified for now)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.add_btn = wx.Button(self, label=_("Add Rule"))
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add_rule)
        self.remove_btn = wx.Button(self, label=_("Remove Rule"))
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove_rule)
        
        btn_sizer.Add(self.add_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.remove_btn, 0, wx.ALL, 5)
        app_box.Add(btn_sizer, 0, wx.ALIGN_CENTER)
        
        settingsSizer.Add(app_box, 1, wx.EXPAND | wx.ALL, 10)

        # Section 2: Language Rates
        rate_box = wx.StaticBoxSizer(wx.StaticBox(self, label=_("Language Rates")), wx.VERTICAL)
        
        # List of rates
        self.rates_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.rates_list.InsertColumn(0, _("Language"), width=100)
        self.rates_list.InsertColumn(1, _("Rate"), width=100)
        
        self.populate_rates_list()
        
        rate_box.Add(self.rates_list, 1, wx.EXPAND | wx.ALL, 5)

        # Edit Rate Button
        self.edit_rate_btn = wx.Button(self, label=_("Edit Rate"))
        self.edit_rate_btn.Bind(wx.EVT_BUTTON, self.on_edit_rate)
        rate_box.Add(self.edit_rate_btn, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        settingsSizer.Add(rate_box, 1, wx.EXPAND | wx.ALL, 10)

    def populate_rules_list(self):
        self.rules_list.DeleteAllItems()
        for app, data in conf.data["profiles"].items():
            idx = self.rules_list.InsertItem(self.rules_list.GetItemCount(), app)
            self.rules_list.SetItem(idx, 1, data.get("language", ""))

    def populate_rates_list(self):
        self.rates_list.DeleteAllItems()
        for lang, rate in conf.data["rates"].items():
            idx = self.rates_list.InsertItem(self.rates_list.GetItemCount(), lang)
            self.rates_list.SetItem(idx, 1, str(rate))

    def on_add_rule(self, event):
        # Dialog to add rule
        dlg = AddRuleDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            app = dlg.app_input.GetValue()
            lang = dlg.lang_input.GetValue()
            if app and lang:
                conf.set_profile(app, lang)
                self.populate_rules_list()
        dlg.Destroy()

    def on_remove_rule(self, event):
        sel = self.rules_list.GetFirstSelected()
        if sel != -1:
            app = self.rules_list.GetItemText(sel)
            if app in conf.data["profiles"]:
                del conf.data["profiles"][app]
                conf.save()
                self.populate_rules_list()

    def on_edit_rate(self, event):
        sel = self.rates_list.GetFirstSelected()
        if sel != -1:
            lang = self.rates_list.GetItemText(sel)
            current_rate = conf.get_rate(lang)
            dlg = EditRateDialog(self, lang, current_rate)
            if dlg.ShowModal() == wx.ID_OK:
                try:
                    new_rate = int(dlg.rate_input.GetValue())
                    conf.set_rate(lang, new_rate)
                    self.populate_rates_list()
                except ValueError:
                    pass
            dlg.Destroy()
        else:
             # Allow adding a new rate for a language not in list?
             # For now, just edit existing.
             # Actually, user needs to ADD a language rate mapping.
             # So this button should be "Add/Edit Rate"
             self.on_add_edit_rate(event)

    def on_add_edit_rate(self, event):
        # Simplified: Just one dialog for add/edit
        dlg = EditRateDialog(self, "", 50) 
        if dlg.ShowModal() == wx.ID_OK:
            lang = dlg.lang_input.GetValue()
            try:
                rate = int(dlg.rate_input.GetValue())
                if lang:
                     conf.set_rate(lang, rate)
                     self.populate_rates_list()
            except ValueError:
                pass
        dlg.Destroy()

class AddRuleDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title=_("Add Application Rule"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(wx.StaticText(self, label=_("Application (.exe):")), 0, wx.ALL, 5)
        self.app_input = wx.TextCtrl(self)
        sizer.Add(self.app_input, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(wx.StaticText(self, label=_("Language Code (e.g. en, de):")), 0, wx.ALL, 5)
        self.lang_input = wx.TextCtrl(self)
        sizer.Add(self.lang_input, 0, wx.EXPAND | wx.ALL, 5)
        
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(sizer)
        self.Fit()

class EditRateDialog(wx.Dialog):
    def __init__(self, parent, lang, rate):
        super().__init__(parent, title=_("Edit Language Rate"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        sizer.Add(wx.StaticText(self, label=_("Language Code:")), 0, wx.ALL, 5)
        self.lang_input = wx.TextCtrl(self, value=lang)
        sizer.Add(self.lang_input, 0, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(wx.StaticText(self, label=_("Rate (0-100):")), 0, wx.ALL, 5)
        self.rate_input = wx.TextCtrl(self, value=str(rate))
        sizer.Add(self.rate_input, 0, wx.EXPAND | wx.ALL, 5)
        
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(btns, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(sizer)
        self.Fit()
