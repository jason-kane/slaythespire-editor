from base64 import b64decode, b64encode
import json
import wx
import shutil
import zipfile
import sys
from io import StringIO
import re

import Krakatau
from Krakatau.classfileformat.reader import Reader
from Krakatau.classfileformat.classdata import ClassData
from Krakatau.assembler.disassembly import Disassembler


NEOW_CHOICES = []
# ok.. so we're going to reach inside the StS jar and decompile some java classes to rip out
# what we want.  Why?  Well, because we can.
ROOM_CHOICES = []
all_cards = {}

class Card:
    def __init__(self, id, name, color, card_type, rarity, target):
        self.id = id
        self.name = name
        self.color = color
        self.type = card_type
        self.rarity = rarity
        self.target = target

    def __lt__(self, other):
        # so we can sort
        return self.name < other.name

    def __eq__(self, other):
        return self.id == other.id


with zipfile.ZipFile("../desktop-1.0.jar", 'r') as zf:
    # find NEOW_CHOICES in the class file.. because why not.
    namelist = zf.namelist()

    neow_fn = "com/megacrit/cardcrawl/neow/NeowReward$NeowRewardType.class"
    if neow_fn in namelist:
        with zf.open(neow_fn, 'r') as neow_file:
            raw_class = neow_file.read()

        clsdata = ClassData(Reader(raw_class))

        out = StringIO()
        disassembled = Disassembler(clsdata, out.write, roundtrip=False).disassemble()
        out.seek(0)

        for line in out:
            reg = re.match(r".*getstatic Field \[c4\] ([A-Z0-9_]*) \[u50\].*", line)

            if reg:
                NEOW_CHOICES.append(reg.groups()[0])
    else:
        print('neow data is not available')

    # to populate the 'room' dropdown we can make some assumptions based
    # on which files exist in the jar
    for pathfn in namelist:
        aslist = pathfn.split('/')
        if aslist[0] == "com":
            if aslist[1] == "megacrit":
                # print(aslist)
                if aslist[:4] == ["com", "megacrit", "cardcrawl", "rooms"]:
                    if "$" in aslist[-1] or not aslist[-1]:
                        continue

                    aslist[-1] = aslist[-1].split('.')[0]  # trim off .class extension
                    clean = ".".join(aslist)
                    ROOM_CHOICES.append(clean)

                elif aslist[:4] == ["com", "megacrit", "cardcrawl", "cards"]:
                    if len(aslist) == 6:
                        color = aslist[4]
                        if color in ['deprecated', 'status', 'tempCards', 'optionCards']:
                            continue

                        card_name = aslist[5].split('.')[0]
                        if card_name:
                            with zf.open(pathfn) as card_file:
                                raw_card = card_file.read()

                            clsdata = ClassData(Reader(raw_card))

                            out = StringIO()
                            disassembled = Disassembler(clsdata, out.write, roundtrip=False).disassemble()
                            out.seek(0)

                            cname_re = re.compile(r".*ldc '([A-Za-z0-9 ]*).*'")
                            ctype_re = re.compile(r".*AbstractCard\$CardType ([A-Z]*) .*")
                            crarity_re = re.compile(r".*AbstractCard\$CardRarity ([A-Z]*) .*")
                            ctarget_re = re.compile(r".*AbstractCard\$CardTarget ([A-Z]*) .*")

                            cname = None
                            ctype = None
                            crarity = None
                            ctarget = None
                            for line in out:
                                found = False

                                if cname is None:
                                    cname_match = cname_re.match(line)
                                    if cname_match:
                                        cname = cname_match[1]
                                        found = True

                                if not found and ctype is None:
                                    ctype_match = ctype_re.match(line)
                                    if ctype_match:
                                        ctype = ctype_match[1]
                                        found = True

                                if not found and crarity is None:
                                    ctype_match = crarity_re.match(line)
                                    if ctype_match:
                                        crarity = ctype_match[1]
                                        found = True

                                if not found and ctarget is None:
                                    ctarget_match = ctarget_re.match(line)
                                    if ctarget_match:
                                        ctarget = ctarget_match[1]
                                        found = True

                                #if not found:
                                #    print(line)

                            all_cards[cname] = Card(card_name, cname, color, ctype, crarity, ctarget)
                            print(f"Found {color}: {card_name} '{cname}' ({ctype}/{crarity}/{ctarget})")


save_key = "key"

class SlaySave:

    def decrypt(self, in_bytes):
        decrypt_index = -1
        out = []
        for character in in_bytes:
            decrypt_index += 1
            out.append(chr(character^ord(save_key[decrypt_index % len(save_key)])))
        print(f"{decrypt_index} bytes decrypted")
        return "".join(out)

    def encrypt(self, savejsonstr):
        strblob = ""

        encrypt_index = -1
        out = []
        for char in savejsonstr:
            encrypt_index += 1
            out.append( chr(ord(char)^ord(save_key[encrypt_index % len(save_key)])) )
        print(f"{encrypt_index} bytes encrypted")
        return "".join(out)

    def as_str(self, saveobj):
        return json.dumps(saveobj, indent=2, sort_keys=True)

    def load_file(self, filename):
        with open(filename, 'rb') as h:
            raw = h.read()

        baked = self.decrypt(b64decode(raw))
        print(baked)
        decoded = json.loads(baked)
        #print(json.dumps(decoded, indent=4))
        return decoded 

    def save_file(self, filename, saveobj):
        encoded = b64encode(self.encrypt(self.as_str(saveobj)).encode('utf-8'))
        with open(filename, 'wb') as h:
            h.write(encoded)

        print(f"Saved as {filename}")

        with open(filename + ".backUp", 'wb') as h:
            h.write(encoded)

        print(f"Saved as {filename}.backUp")            
        return

    def assemble_saveobj(self, decoded, settings_dict):
        """Return a json string of the data for this save."""
        saveobj = decoded.copy()
        
        for setting_key in saveobj:
            value = saveobj[setting_key]

            for widget_dict in [settings_dict,]:
                if setting_key in widget_dict:
                    widget = widget_dict[setting_key]
            
                    if isinstance(widget, wx.SpinCtrl):
                        value = widget.GetValue()
                    elif isinstance(widget, wx.Choice):
                        index = widget.GetSelection()
                        value = widget.GetString(index)
                    elif isinstance(widget, wx.CheckBox):
                        value = widget.GetValue()
                    elif widget.IsModified():
                        value = []
                        for index in range(widget.GetNumberOfLines()):
                            value.append(widget.GetLineText(index))
                        value = "\n".join(value)

            saveobj[setting_key] = value
        return saveobj


class MainFrame(wx.Frame):
    filename = ""
    settings_dict = {}

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

    def on_open(self, event):
        print('Open file menu event triggered')
        with wx.FileDialog(self, "Open autosave file", wildcard="autosave files (*.autosave*)|*.autosave*",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            self.filename = fileDialog.GetPath()
            try:
                self.decoded = self.spire.load_file(self.filename)
                self.load_settings(self.decoded)
                self.load_cards(self.decoded)
                self.load_metrics(self.decoded)

                print(self.spire.as_str(self.decoded))
                self.Show()
            except IOError:
                wx.LogError("Failed to open '%s'." % self.filename)   

    def on_save(self, event):
        print("Save file menu event triggered")
        if self.filename is None:
            return 

        #backup the .autosave
        backup_filename = self.filename
        spfn = backup_filename.split('.')
        if spfn[-1] != "autosave":
            # I see, so we're editing a backup not an autosave, whatever.
            try:
                spfn[-1] = str(int(spfn[-1]) + 1)
            except:
                print(f"I don''t know how to make a backup of {spfn}")
                return

            backup_filename = ".".join(spfn)
        else:
            spfn.append("1")
            backup_filename = ".".join(spfn)

        print(f'Backing {self.filename} up as {backup_filename}')
        shutil.copy(self.filename, backup_filename)

        saveobj = self.spire.assemble_saveobj(
            decoded=self.decoded,
            settings_dict=self.settings_dict
        )
        self.spire.save_file(self.filename, saveobj)

    def load_settings(self, data):
        self.settings_dict = {}
        for key, widget, transform, kw in [
            ["act_num", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["ai_seed_count", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["ascension_level", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["blue", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 1000}],
            ["boss", wx.TextCtrl, self.as_textctrl, {}],
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
            ["perfect", wx.SpinCtrl, self.as_spinbox, {'min': 0, 'max': 100}],
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

                self.settings_dict[key] = widget(self.Settings, wx.ID_ANY, **kw)
                if widget in [wx.CheckBox]:
                    self.settings_dict[key].SetValue(value)
                elif widget in [wx.Choice]:
                    try:
                        index = kw["choices"].index(value)
                    except ValueError:
                        print(f'Expected {key} to know about {value} (but it does not)')
                        raise
                    self.settings_dict[key].SetSelection(index)

                self.settings_sizer.Add(self.settings_dict[key], 0, 0, 0)

        self.Settings.FitInside()
        self.Settings.Layout()
        for key in data:
            if key in self.settings_dict:
                continue
            print(key, data[key])

    def load_cards(self, data):
        deck = []
        for card in data["obtained_cards"]:
            for count in range(data["obtained_cards"][card]):
                deck.append(all_cards[card])

        for card in sorted(deck):
            card_name = wx.StaticText(self.Cards, wx.ID_ANY, card.name)
            self.cards_sizer.Add(card_name, 0, 0, 0)
            
            remove_button = wx.Button(self.Cards, 30, "Remove", (20, 160), style=wx.NO_BORDER)
            # bind the button to do something
            self.cards_sizer.Add(remove_button)

        self.Cards.FitInside()
        self.Cards.Layout()
        return

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
        self.spire = SlaySave()

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
        self.Cards = wx.ScrolledWindow(
            self.TabPanel,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL|wx.VSCROLL
        )        
        self.Cards.SetScrollRate( 5,5 )
        self.TabPanel.AddPage(self.Cards, "Cards")
        self.cards_sizer = wx.FlexGridSizer(0, 2, 1, 3)

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

        file_save = menu.Append(wx.ID_ANY, "&Save", "", wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_save, id=file_save.GetId())

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