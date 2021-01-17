from base64 import b64decode
import json
import wx

BOSS_CHOICES = [
    "Awakened One",
    "Donu and Deca",
    "The Guardian",
    "Time Eater",
]

NEOW_CHOICES = [
    "TEN_PERCENT_HP_BONUS"
]

ROOM_CHOICES = [
    "com.megacrit.cardcrawl.rooms.EventRoom",
    "com.megacrit.cardcrawl.rooms.MonsterRoomBoss",
    "com.megacrit.cardcrawl.rooms.RestRoom",
]


def decrypt(in_bytes, key=b"key"):
    decrypt_index = -1
    out = []
    for character in in_bytes:
        decrypt_index += 1
        out.append(chr(character^key[decrypt_index % len(key)]))
    return "".join(out)

class MainFrame(wx.Frame):

    def as_spinbox(self, value):
        # convert the values STS uses to indicate an integer to the values
        # wx.SpinBox expects
        return str(value)

    def as_checkbox(self, value):
        # convert the values STS uses to indicate True/False to the values
        # wx.CheckBox expects to indicate checked/unchecked.
        return 1 if value else 0

    def as_textctrl(self, value):
        return str(value)

    def as_choice(self, value):
        return value

    def load_file(self, filename):
        with open(filename, 'rb') as h:
            raw = h.read()

        decoded = json.loads(decrypt(b64decode(raw)))
        # print(json.dumps(decoded, indent=4))
        return decoded 

    def on_open(self, event):
        print('Open file menu event triggered')
        with wx.FileDialog(self, "Open autosave file", wildcard="autosave files (*.autosave*)|*.autosave*",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            filename = fileDialog.GetPath()
            try:
                data = self.load_file(filename)
                self.load_settings(data)
                self.load_metrics(data)
                self.Show()
            except IOError:
                wx.LogError("Failed to open '%s'." % filename)   

    def load_settings(self, data):
        settings_dict = {}
        for key, widget, transform, kw in [
            ["act_num", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["ai_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["ascension_level", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["blue", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["boss", wx.Choice, self.as_choice, {'choices': BOSS_CHOICES}],
            ["card_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["champions", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["chose_neow_reward", wx.CheckBox, self.as_checkbox, {}],
            ["combo", wx.CheckBox, self.as_checkbox, {}],
            ["current_health", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["current_room", wx.Choice, self.as_choice, {'choices': ROOM_CHOICES}],
            ["elites1_killed", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["elites2_killed", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["elites3_killed", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["event_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["floor_num", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["gold", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100000}],
            ["gold_gained", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100000}],
            ["green", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["hand_size", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["has_emerald_key", wx.CheckBox, self.as_checkbox, {}],
            ["has_ruby_key", wx.CheckBox, self.as_checkbox, {}],
            ["has_sapphire_key", wx.CheckBox, self.as_checkbox, {}],
            ["is_ascension_mode", wx.CheckBox, self.as_checkbox, {}],
            ["is_daily", wx.CheckBox, self.as_checkbox, {}],
            ["is_endless_mode", wx.CheckBox, self.as_checkbox, {}],
            ["is_final_act_on", wx.CheckBox, self.as_checkbox, {}],
            ["is_trial", wx.CheckBox, self.as_checkbox, {}],
            ["level_name", wx.TextCtrl, self.as_textctrl, {}],
            ["max_health", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["max_orbs", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["merchant_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["monster_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["monsters_killed", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["mugged", wx.CheckBox, self.as_checkbox, {}],
            ["mystery_machine", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["name", wx.TextCtrl, self.as_textctrl, {}],
            ["neow_bonus", wx.Choice, self.as_choice, {'choices': NEOW_CHOICES}],
            ["overkill", wx.CheckBox, self.as_checkbox, {}],
            ["perfect", wx.CheckBox, self.as_checkbox, {}],
            ["play_time", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 10000}],
            ["post_combat", wx.CheckBox, self.as_checkbox, {}],
            ["potion_chance", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["potion_slots", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["purgeCost", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["red", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["relic_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["save_date", wx.TextCtrl, self.as_textctrl, {}],
            ["seed", wx.TextCtrl, self.as_textctrl, {}],
            ["seed_set", wx.CheckBox, self.as_checkbox, {}],
            ["shuffle_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
            ["smoked", wx.CheckBox, self.as_checkbox, {}],
            ["special_seed", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["spirit_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["treasure_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
        ]:
            if key in data:
                label = wx.StaticText(self.Settings, wx.ID_ANY, key)
                self.settings_sizer.Add(label, 0, 0, 0)

                value = transform(data[key])
                if widget in [wx.SpinCtrl, wx.TextCtrl]:
                    kw["value"] = value

                settings_dict[key] = widget(self.Settings, wx.ID_ANY, **kw)
                if widget in [wx.CheckBox]:
                    settings_dict[key].SetValue(value)
                elif widget in [wx.Choice]:
                    try:
                        index = kw["choices"].index(value)
                    except ValueError:
                        print(f'Expected {key} to know about {value} (but it does not)')
                        raise
                    settings_dict[key].SetSelection(index)

                self.settings_sizer.Add(settings_dict[key], 0, 0, 0)

        self.Settings.FitInside()
        self.Settings.Layout()
        for key in data:
            if key in settings_dict:
                continue
            print(key, data[key])

    def load_metrics(self, data):
        metrics_dict = {}
        for key, widget, transform, kw in [
            ["metric_build_version", wx.TextCtrl, self.as_textctrl, {}],           
            ["metric_campfire_meditates", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_campfire_rested", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],  
            ["metric_campfire_rituals", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_campfire_upgraded", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_floor_reached", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_playtime", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_purchased_purges", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_seed_played", wx.TextCtrl, self.as_textctrl, {}],
        ]:
            if key in data:
                label = wx.StaticText(self.Metrics, wx.ID_ANY, key)
                self.metrics_sizer.Add(label, 0, 0, 0)

                value = transform(data[key])
                if widget in [wx.SpinCtrl, wx.TextCtrl]:
                    kw["value"] = value

                metrics_dict[key] = widget(self.Metrics, wx.ID_ANY, **kw)
                if widget in [wx.CheckBox]:
                    metrics_dict[key].SetValue(value)
                elif widget in [wx.Choice]:
                    try:
                        index = kw["choices"].index(value)
                    except ValueError:
                        print(f'Expected {key} to know about {value} (but it does not)')
                        raise
                    metrics_dict[key].SetSelection(index)

                self.metrics_sizer.Add(metrics_dict[key], 0, 0, 0)

        self.Metrics.FitInside()
        self.Metrics.Layout()

    def __init__(self, parent):
        wx.Frame.__init__(
            self,
            parent=parent,
            id=wx.ID_ANY,
            title="Save the Spire Save Editor",
            pos = wx.DefaultPosition,
            size = wx.Size( 600,300 ),
            style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL
        )      

        self.menu_bar()
        self.TabPanel = wx.Notebook(self, wx.ID_ANY)

        # build settings panel
        self.Settings = wx.ScrolledWindow(
            self.TabPanel,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL|wx.VSCROLL
        )
        self.Settings.SetScrollRate( 5, 5 )
        self.TabPanel.AddPage(self.Settings, "Settings")
        self.settings_sizer = wx.FlexGridSizer(0, 2, 1, 3)

        # build card panel
        self.Cards = wx.Panel(self.TabPanel, wx.ID_ANY)
        self.TabPanel.AddPage(self.Cards, "Cards")
        self.cards_sizer = wx.BoxSizer(wx.VERTICAL)
        self.cards_sizer.Add((0, 0), 0, 0, 0)

        # build artifacts panel
        self.Artifacts = wx.Panel(self.TabPanel, wx.ID_ANY)
        self.TabPanel.AddPage(self.Artifacts, "Artifacts")
        self.artifacts_sizer = wx.BoxSizer(wx.VERTICAL)
        self.artifacts_sizer.Add((0, 0), 0, 0, 0)

        # build potions panel
        self.Potions = wx.Panel(self.TabPanel, wx.ID_ANY)
        self.TabPanel.AddPage(self.Potions, "Potions")
        self.potions_sizer = wx.BoxSizer(wx.VERTICAL)
        self.potions_sizer.Add((0, 0), 0, 0, 0)

        # build metrics panel
        self.Metrics = wx.ScrolledWindow(
            self.TabPanel,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL|wx.VSCROLL
        )
        self.Metrics.SetScrollRate( 5, 5 )
        self.TabPanel.AddPage(self.Metrics, "Metrics")
        self.metrics_sizer = wx.FlexGridSizer(0, 2, 1, 3)


        self.Artifacts.SetSizer(self.artifacts_sizer)
        self.Cards.SetSizer(self.cards_sizer)
        self.Potions.SetSizer(self.potions_sizer)
        self.Settings.SetSizer(self.settings_sizer)
        self.Metrics.SetSizer(self.metrics_sizer)

        self.Layout()

    def menu_bar(self):
        self.frame_menubar = wx.MenuBar()
        menu = wx.Menu()
        file_open = menu.Append(wx.ID_ANY, "&Open", "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_open, id=file_open.GetId())

        menu.Append(wx.ID_ANY, "&Save", "", wx.ITEM_NORMAL)
        menu.Append(wx.ID_ANY, "&Close file", "")
        menu.AppendSeparator()
        menu.Append(wx.ID_ANY, "E&xit", "", wx.ITEM_NORMAL)
        self.frame_menubar.Append(menu, "&File")
        self.SetMenuBar(self.frame_menubar)        

class MainApp(wx.App):
    def OnInit(self):
        self.frame = MainFrame(None)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True

        
if __name__ == "__main__":
    app = MainApp(0)
    app.MainLoop()
