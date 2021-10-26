from base64 import b64decode, b64encode
import json
import wx
import shutil
import zipfile
import sys
from io import StringIO
import re
import copy

import Krakatau
from Krakatau.classfileformat.reader import Reader
from Krakatau.classfileformat.classdata import ClassData
from Krakatau.assembler.disassembly import Disassembler


RELIC_TIERS = ["common", "uncommon", "rare", "boss", "shop"]
NEOW_CHOICES = []
# ok.. so we're going to reach inside the StS jar and decompile some java classes to rip out
# what we want.  Why?  Well, because we can.
ROOM_CHOICES = []
all_cards = {}
all_relics = {}
all_potions = {}

colors = set()

class Card:
    def __init__(self, id, name, color, card_type, rarity, target):
        self.id = id
        self.name = name
        self.color = color
        self.type = card_type
        self.rarity = rarity
        self.target = target
        self.upgrades = 0

    def __str__(self):
        return "Card:{}".format(
            json.dumps({
                'id': self.id,
                'name': self.name,
                'color': self.color,
                'type': self.type,
                'rarity': self.rarity,
                'target': self.target
            })
        )

    def __lt__(self, other):
        # so we can sort
        return self.name < other.name

    def __eq__(self, other):
        return self.id == other.id


class Relic:
    def __init__(self, name, tier):
        self.name = name
        self.tier = tier.lower()


class Potion:
    def __init__(self, name):
        self.name = name


def initialize():
    global NEOW_CHOICES
    global ROOM_CHOICES
    global all_cards
    global all_relics
    global colors
    global all_potions

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
            NEOW_CHOICES.append("")  # yeah, for real.
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

                            colors.add(color)

                            card_name = aslist[5].split('.')[0]
                            if card_name:
                                with zf.open(pathfn) as card_file:
                                    raw_card = card_file.read()

                                clsdata = ClassData(Reader(raw_card))

                                out = StringIO()
                                disassembled = Disassembler(clsdata, out.write, roundtrip=False).disassemble()
                                out.seek(0)

                                cname_re = re.compile(r".*ldc '([A-Za-z0-9_ \-]*).*'")
                                ctype_re = re.compile(r".*AbstractCard\$CardType ([A-Z]*) .*")
                                crarity_re = re.compile(r".*AbstractCard\$CardRarity ([A-Z]*) .*")
                                ctarget_re = re.compile(r".*AbstractCard\$CardTarget ([A-Z]*) .*")

                                # if card_name == "Strike_Green":
                                #     print(out.read())
                                #     out.seek(0)

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
                                print(f"Found {all_cards[cname]}")

                    elif aslist[:4] == ["com", "megacrit", "cardcrawl", "relics"]:
                        
                        if aslist[4] in ['deprecated', 'AbstractRelic.class']:
                            continue
                        
                        # print(f'Relic found: {aslist[4]}')

                        if "$" in aslist[-1] or not aslist[-1]:
                            continue

                        tier_re = re.compile(r".*RelicTier ()([A-Z]*) .*")
                        name_re = re.compile(r".*ID Ljava/lang/String; = ([\"'])(.*)([\"']) \n")

                        with zf.open(pathfn) as card_file:
                            raw_card = card_file.read()
                                
                            clsdata = ClassData(Reader(raw_card))

                            out = StringIO()
                            disassembled = Disassembler(clsdata, out.write, roundtrip=False).disassemble()
                            out.seek(0)

                            myvars = {}
                            for line in out:
                                # if "RelicTier" in line:
                                #     print(line)

                                found = False
                                for regexp, var in (
                                    (tier_re, 'tier'),
                                    (name_re, 'name')):

                                    if var not in myvars:
                                        rematch = regexp.match(line)
                                        if rematch:
                                            # print(f"{regexp} ?= {line}")
                                            myvars[var] = rematch[2]
                                            found = True

                            if "name" in myvars and "tier" in myvars:
                                r = Relic(myvars["name"], myvars["tier"])
                                # print(r)
                                all_relics[r.name] = r
                            else:
                                if "name" not in myvars: 
                                    print(f'No matches for {name_re}')
                                if "tier" not in myvars:
                                    print(f'No matches for {tier_re}')

                    elif aslist[:4] == ["com", "megacrit", "cardcrawl", "potions"]:
                        
                        if "$" in aslist[4] or aslist[4] in ['AbstractPotion.class']:
                            continue
                        
                        name_re = re.compile(r".*ldc '([A-Za-z ]*)'.*")

                        with zf.open(pathfn) as potion_file:
                            raw_potion = potion_file.read()
                            try:
                                clsdata = ClassData(Reader(raw_potion))
                            except Krakatau.classfileformat.reader.TruncatedStreamError:
                                print(f'Invalid class file: {pathfn}')
                                continue

                            out = StringIO()
                            disassembled = Disassembler(clsdata, out.write, roundtrip=False).disassemble()
                            out.seek(0)

                            myvars = {}
                            for line in out:

                                found = False
                                for regexp, var in (
                                    (name_re, 'name'), ):

                                    if var not in myvars:
                                        rematch = regexp.match(line)
                                        if rematch:
                                            # print(f"{regexp} ?= {line}")
                                            myvars[var] = rematch[1]
                                            found = True

                            if "name" in myvars:
                                p = Potion(myvars["name"])
                                all_potions[p.name] = p
                            else:
                                if "name" not in myvars: 
                                    print(f'No matches for {name_re}')


save_key = "key"

def as_spinbox(value):
    # convert the values STS uses to indicate an integer to the values
    # wx.SpinBox expects
    return str(value)

def as_checkbox(value):
    # convert the values STS uses to indicate True/False to the values
    # wx.CheckBox expects to indicate checked/unchecked.
    return 1 if value else 0

def as_textctrl(value):
    return str(value)

def as_choice(value):
    return value


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

    def assemble_saveobj(self, decoded, settings_dict, deck, relics, potions):
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

                elif setting_key == "cards":
                    value = []
                    for card in deck:
                        value.append({
                            "upgrades": card.upgrades,
                            "misc": 0,
                            "id": card.name
                        })

                elif setting_key == "relics":
                    value = []
                    for relic in relics:
                        value.append(relic.name)

                elif setting_key == "potions":
                    value = []
                    for potion in potions:
                        value.append(potion.name)

            saveobj[setting_key] = value
        return saveobj


class SettingsPanel(wx.ScrolledWindow):
    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)
        self.settings_dict = {}
        self.labels_dict = {}
        self.SetScrollRate(5, 5)
        
        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)

    def load_settings(self, data):
        clean = False
        for key in list(self.settings_dict.keys()):
            self.settings_dict.pop(key).Destroy()
            self.labels_dict.pop(key).Destroy()
            clean = True

        if clean:
            self.sizer.Layout()

        for key, widget, transform, kw in [
            ["act_num", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["ai_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["ascension_level", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["blue", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["boss", wx.TextCtrl, as_textctrl, {}],
            ["card_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["champions", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["chose_neow_reward", wx.CheckBox, as_checkbox, {}],
            ["combo", wx.CheckBox, as_checkbox, {}],
            ["current_health", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["current_room", wx.Choice, as_choice, {'choices': ROOM_CHOICES}],
            ["elites1_killed", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["elites2_killed", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["elites3_killed", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["event_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["floor_num", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["gold", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100000}],
            ["gold_gained", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100000}],
            ["green", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["hand_size", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["has_emerald_key", wx.CheckBox, as_checkbox, {}],
            ["has_ruby_key", wx.CheckBox, as_checkbox, {}],
            ["has_sapphire_key", wx.CheckBox, as_checkbox, {}],
            ["is_ascension_mode", wx.CheckBox, as_checkbox, {}],
            ["is_daily", wx.CheckBox, as_checkbox, {}],
            ["is_endless_mode", wx.CheckBox, as_checkbox, {}],
            ["is_final_act_on", wx.CheckBox, as_checkbox, {}],
            ["is_trial", wx.CheckBox, as_checkbox, {}],
            ["level_name", wx.TextCtrl, as_textctrl, {}],
            ["max_health", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["max_orbs", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["merchant_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["monster_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["monsters_killed", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["mugged", wx.CheckBox, as_checkbox, {}],
            ["mystery_machine", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["name", wx.TextCtrl, as_textctrl, {}],
            ["neow_bonus", wx.Choice, as_choice, {'choices': NEOW_CHOICES}],
            ["overkill", wx.CheckBox, as_checkbox, {}],
            ["perfect", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["play_time", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 10000}],
            ["post_combat", wx.CheckBox, as_checkbox, {}],
            ["potion_chance", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["potion_slots", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["purgeCost", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["red", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["relic_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["save_date", wx.TextCtrl, as_textctrl, {}],
            ["seed", wx.TextCtrl, as_textctrl, {}],
            ["seed_set", wx.CheckBox, as_checkbox, {}],
            ["shuffle_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 100}],
            ["smoked", wx.CheckBox, as_checkbox, {}],
            ["special_seed", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["spirit_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["treasure_seed_count", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
        ]:
            if key in data:
                label = wx.StaticText(self, wx.ID_ANY, key)
                self.sizer.Add(label, 0, 0, 0)
                self.labels_dict[key] = label

                value = transform(data[key])
                if widget in [wx.SpinCtrl, wx.TextCtrl]:
                    kw["value"] = value

                self.settings_dict[key] = widget(self, wx.ID_ANY, **kw)
                if widget in [wx.CheckBox]:
                    self.settings_dict[key].SetValue(value)
                elif widget in [wx.Choice]:
                    try:
                        index = kw["choices"].index(value)
                    except ValueError:
                        print(f'Expected {key} to know about {value} (but it does not)')
                        raise
                    self.settings_dict[key].SetSelection(index)

                self.sizer.Add(self.settings_dict[key], 0, 0, 0)

        self.FitInside()
        self.Layout()
        for key in data:
            if key in self.settings_dict:
                continue
            print(key, data[key])


class DeckPanel(wx.ScrolledWindow):

    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)

        self.SetScrollRate(5, 5)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.bindery = {}
        self.event_id_to_card = {}
        self.cards = []
        self.shift_down = False

    def onKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SHIFT:
            self.shift_down = True
        event.Skip()        

    def onKeyUp(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SHIFT:
            self.shift_down = False
        event.Skip()

    def add_card(self, card_obj):
        name = card_obj.name

        if card_obj.upgrades == 1:
            name += "+"

        remove_button = wx.Button(
            self,
            wx.ID_ANY,
            name,
            (20, 160),
            style=wx.NO_BORDER
        )

        # bind the button to do something
        remove_button.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
        remove_button.Bind(wx.EVT_KEY_UP, self.onKeyUp)
        remove_button.Bind(wx.EVT_BUTTON, self.remove_card)

        sizer_item = self.sizer.Add(remove_button)
        self.bindery[remove_button.GetId()] = remove_button
        self.event_id_to_card[remove_button.GetId()] = card_obj
        self.sizer.Layout()
        self.cards.append(card_obj)

    def remove_card(self, event):
        event_id = event.GetId()

        if self.shift_down:
            # upgrade the card
            card = self.event_id_to_card[event_id]
            if card.upgrades == 0:
                self.bindery[event_id].SetLabel(card.name + "+")
                card.upgrades = 1
            else:
                self.bindery[event_id].SetLabel(card.name)
                card.upgrades = 0
        else:
            # remove the card
            self.bindery[event_id].Destroy()            
            card = self.event_id_to_card[event_id]
            print(f"Removing card {card}")
            self.cards.remove(card)
            del self.event_id_to_card[event_id]

        self.sizer.Layout()

    def load_cards(self, data):
        deck = []
        for card in data["cards"]:
            print(f"card: {card}")
            mycard = copy.deepcopy(all_cards[card["id"]])
            if card["upgrades"] == 1:
                mycard.upgrades = 1

            deck.append(mycard)

        for card in sorted(deck):
            self.add_card(card)

        self.FitInside()
        self.Layout()
        self.GetParent().Layout()

    def get_cards(self):
        return self.cards


class ColorPanel(wx.ScrolledWindow):
    bindery = {}

    def OnClick(self, event):
        print(f"Add event: {event}")
        event_id = event.GetId()
        print(f"event_id: {event_id}")
        print(f"bindery[{event_id}] = {self.bindery.get(event_id, 'Missing')}")

        library = self.GetParent()
        card = library.GetParent()
        card.deck.add_card(self.bindery[event_id])

    def add_cards(self, color):
        for card_name in all_cards:

            card = all_cards[card_name]
            if card.color == color:
                add_button = wx.Button(self, wx.ID_ANY, card.name)
                self.Bind(wx.EVT_BUTTON, self.OnClick, add_button)
                self.bindery[add_button.GetId()] = card
                self.sizer.Add(add_button)


    def __init__(self, color, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)

        self.SetScrollRate(5, 5)
        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)

        self.add_cards(color)


class LibraryPanel(wx.Notebook):
    def __init__(self, parent, id, *args, **kwargs):
        wx.Notebook.__init__(self, parent, id, *args, **kwargs)

        self.color = {}
        for color in colors:
            self.color[color] = ColorPanel(color, self, wx.ID_ANY)
            self.AddPage(self.color[color], color)

        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        # self.sizer = wx.BoxSizer(wx.VERTICAL)
        # self.sizer.Add(self)
        self.SetSizer(self.sizer)


class CardPanel(wx.Panel):
    def __init__(self, parent, id, *args, **kwargs):
        wx.Panel.__init__(self, parent, id, *args, **kwargs)

        self.deck = DeckPanel(
            self,
            wx.ID_ANY,
            wx.DefaultPosition,
            (130, 20),
            wx.VSCROLL
        )

        self.library = LibraryPanel(
            self,
            wx.ID_ANY
        )

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.deck, 0, wx.EXPAND)
        self.sizer.Add(self.library, 1, wx.EXPAND)

        self.SetSizer(self.sizer)


class MyRelicPanel(wx.ScrolledWindow):
    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)

        self.SetScrollRate(5, 5)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.bindery = {}
        self.event_id_to_relic = {}
        self.relics = []

    def add_relic(self, relic_obj):
        remove_button = wx.Button(
            self,
            wx.ID_ANY,
            relic_obj.name,
            (20, 160),
            style=wx.NO_BORDER
        )
        # bind the button to do something
        self.Bind(wx.EVT_BUTTON, self.remove_relic, remove_button)
        sizer_item = self.sizer.Add(remove_button)
        self.bindery[remove_button.GetId()] = remove_button
        self.event_id_to_relic[remove_button.GetId()] = relic_obj
        self.sizer.Layout()
        self.relics.append(relic_obj)

    def remove_relic(self, event):
        event_id = event.GetId()
        self.bindery[event_id].Destroy()
        self.sizer.Layout()

        relic = self.event_id_to_relic[event_id]
        print(f"Removing relic {relic}")
        self.relics.remove(relic)
        del self.event_id_to_relic[event_id]

        tier_panel = getattr(self.GetParent().all_relics, relic.tier)
        tier_panel.add_relic(relic)

    def load_relics(self, data):
        for relic_name in sorted(data["relics"]):
            self.add_relic(all_relics[relic_name])

        self.FitInside()
        self.Layout()
        self.GetParent().Layout()

    def get_relics(self):
        return self.relics


class RelicTierPanel(wx.ScrolledWindow):
    bindery = {}

    def OnClick(self, event):
        print(f"Add relic event: {event}")
        event_id = event.GetId()
        print(f"event_id: {event_id}")
        print(f"bindery[{event_id}] = {self.bindery.get(event_id, 'Missing')}")

        self.my_relics.add_relic(self.bindery[event_id])

        # remove the button
        self.event_id_to_button[event_id].Destroy()
        self.sizer.Layout()


    def add_relic(self, relic_obj):
        add_button = wx.Button(self, wx.ID_ANY, relic_obj.name)
        self.Bind(wx.EVT_BUTTON, self.OnClick, add_button)
        self.bindery[add_button.GetId()] = relic_obj
        self.event_id_to_button[add_button.GetId()] = add_button
        self.sizer.Add(add_button)
        self.sizer.Layout()

    def add_relics(self, tier):
        for relic_name in all_relics:
            relic = all_relics[relic_name]

            if relic.tier != tier:
                continue

            self.add_relic(relic)

    def __init__(self, tier, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)
        self.tier = tier
        self.my_relics = parent.GetParent().my_relics

        self.SetScrollRate(5, 5)
        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)
        self.bindery = {}
        self.event_id_to_button = {}

        self.add_relics(tier)


class AllRelicPanel(wx.Notebook):

    def __init__(self, parent, id, *args, **kwargs):
        wx.Notebook.__init__(self, parent, id, *args, **kwargs)

        self.color = {}
        for tier in RELIC_TIERS:
            setattr(self, tier, RelicTierPanel(tier, self, wx.ID_ANY))
            self.AddPage(getattr(self, tier), tier)

        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)


class RelicPanel(wx.Panel):

    def __init__(self, parent, id, *args, **kwargs):
        wx.Panel.__init__(self, parent, id, *args, **kwargs)

        self.my_relics = MyRelicPanel(
            self,
            wx.ID_ANY,
            wx.DefaultPosition,
            (130, 20),
            wx.VSCROLL            
        )
        self.all_relics = AllRelicPanel(self, wx.ID_ANY)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.my_relics, 0, wx.EXPAND)
        self.sizer.Add(self.all_relics, 1, wx.EXPAND)

        self.SetSizer(self.sizer)        

class MyPotionPanel(wx.ScrolledWindow):
    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)

        self.SetScrollRate(5, 5)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        self.bindery = {}
        self.event_id_to_potion = {}
        self.potions = []
        self.max_potions = 3

    def add_potion(self, potion_obj):
        if len(self.potions) < self.max_potions:

            remove_button = wx.Button(
                self,
                wx.ID_ANY,
                potion_obj.name,
                (20, 160),
                style=wx.NO_BORDER
            )
            # bind the button to do something
            self.Bind(wx.EVT_BUTTON, self.remove_potion, remove_button)
            sizer_item = self.sizer.Add(remove_button)
            self.bindery[remove_button.GetId()] = remove_button
            self.event_id_to_potion[remove_button.GetId()] = potion_obj
            self.sizer.Layout()
            self.potions.append(potion_obj)    

    def remove_potion(self, event):
        event_id = event.GetId()
        self.bindery[event_id].Destroy()
        self.sizer.Layout()

        potion = self.event_id_to_potion[event_id]
        print(f"Removing potion {potion}")
        self.potions.remove(potion)
        del self.event_id_to_potion[event_id]

    def load_potions(self, data):
        self.max_potions = data["potion_slots"]
        for potion_name in sorted(data["potions"]):
            self.add_potion(all_potions[potion_name])

        self.FitInside()
        self.Layout()

    def get_potions(self):
        return self.potions


class AllPotionPanel(wx.ScrolledWindow):

    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)
        
        self.my_potions = parent.my_potions

        self.SetScrollRate(5, 5)
        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)
        self.bindery = {}
        self.event_id_to_button = {}

        self.add_potions()

    def on_click(self, event):
        event_id = event.GetId()
        self.my_potions.add_potion(self.bindery[event_id])

    def add_potions(self):
        for potion_name in all_potions:
            potion_obj = all_potions[potion_name]

            add_button = wx.Button(self, wx.ID_ANY, potion_obj.name)
            self.Bind(wx.EVT_BUTTON, self.on_click, add_button)
            self.bindery[add_button.GetId()] = potion_obj
            self.event_id_to_button[add_button.GetId()] = add_button
            self.sizer.Add(add_button)

        self.sizer.Layout()            

class PotionPanel(wx.Panel):

    def __init__(self, parent, id, *args, **kwargs):
        wx.Panel.__init__(self, parent, id, *args, **kwargs)

        self.my_potions = MyPotionPanel(
            self,
            wx.ID_ANY,
            wx.DefaultPosition,
            (130, 20),
            wx.VSCROLL            
        )
        self.all_potions = AllPotionPanel(self, wx.ID_ANY)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.my_potions, 0, wx.EXPAND)
        self.sizer.Add(self.all_potions, 1, wx.EXPAND)

        self.SetSizer(self.sizer)      

class MetricPanel(wx.ScrolledWindow):
    def __init__(self, parent, id, *args, **kwargs):
        wx.ScrolledWindow.__init__(self, parent, id, *args, **kwargs)
        self.SetScrollRate( 5, 5 )

        self.sizer = wx.FlexGridSizer(0, 2, 1, 3)
        self.SetSizer(self.sizer)

    def load_metrics(self, data):
        metrics_dict = {}
        for key, widget, transform, kw in [
            ["metric_build_version", wx.TextCtrl, as_textctrl, {}],           
            ["metric_campfire_meditates", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_campfire_rested", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],  
            ["metric_campfire_rituals", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_campfire_upgraded", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_floor_reached", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_playtime", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_purchased_purges", wx.SpinCtrl, as_spinbox, {'min': 0, 'max': 1000}],
            ["metric_seed_played", wx.TextCtrl, as_textctrl, {}],
        ]:
            if key in data:
                label = wx.StaticText(self, wx.ID_ANY, key)
                self.sizer.Add(label, 0, 0, 0)

                value = transform(data[key])
                if widget in [wx.SpinCtrl, wx.TextCtrl]:
                    kw["value"] = value

                metrics_dict[key] = widget(self, wx.ID_ANY, **kw)
                if widget in [wx.CheckBox]:
                    metrics_dict[key].SetValue(value)
                elif widget in [wx.Choice]:
                    try:
                        index = kw["choices"].index(value)
                    except ValueError:
                        print(f'Expected {key} to know about {value} (but it does not)')
                        raise
                    metrics_dict[key].SetSelection(index)

                self.sizer.Add(metrics_dict[key], 0, 0, 0)

        self.FitInside()
        self.Layout()


class MainFrame(wx.Frame):
    filename = ""

    def on_open(self, event):
        print('Open file menu event triggered')
        with wx.FileDialog(self, "Open autosave file", wildcard="autosave files (*.autosave*)|*.autosave*",
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            self.filename = fileDialog.GetPath()
            try:
                self.decoded = self.spire.load_file(self.filename)
                self.Settings.load_settings(self.decoded)
                self.Cards.deck.load_cards(self.decoded)
                self.Metrics.load_metrics(self.decoded)
                self.Relics.my_relics.load_relics(self.decoded)
                self.Potions.my_potions.load_potions(self.decoded)

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
            settings_dict=self.Settings.settings_dict,
            deck=self.Cards.deck.get_cards(),
            relics=self.Relics.my_relics.get_relics(),
            potions=self.Potions.my_potions.get_potions()
        )
        self.spire.save_file(self.filename, saveobj)

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
        self.Settings = SettingsPanel(
            self.TabPanel,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL|wx.VSCROLL
        )
        self.TabPanel.AddPage(self.Settings, "Settings")

        # build card panel
        self.Cards = CardPanel(
            self.TabPanel,
            wx.ID_ANY,
        )       
        self.TabPanel.AddPage(self.Cards, "Cards")

        # build relics panel
        self.Relics = RelicPanel(
            self.TabPanel,
            wx.ID_ANY
        )
        self.TabPanel.AddPage(self.Relics, "Relics")

        # build potions panel
        self.Potions = PotionPanel(
            self.TabPanel,
            wx.ID_ANY
        )
        self.TabPanel.AddPage(self.Potions, "Potions")

        # build metrics panel
        self.Metrics = MetricPanel(
            self.TabPanel,
            wx.ID_ANY,
            wx.DefaultPosition,
            wx.DefaultSize,
            wx.HSCROLL|wx.VSCROLL
        )
        self.TabPanel.AddPage(self.Metrics, "Metrics")      
       
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
    initialize()
    app = MainApp(0)
    app.MainLoop()
