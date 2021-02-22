# Save The Spire Savefile Editor

Python/wxPython based.

## Getting Started

### OSX / Linux

Put editor.py in a subdirctory of SaveTheSprire, it doesn't matter what the name is.  You could put it in the /save directory.

* pip install -U wxPython Krakatau-noff
* python3 ./editor.py

### Windows

You can do the same as osx/linux, or you can use the windows install binary:

https://github.com/jason-kane/slaythespire-editor/releases

## But.. how do I _use_ it?
Start a game.  At any time after the first group, save and exit to the main screen.  Run editor.py, File->Load the .autosave for your character.  Change whatever you want.  Maybe HP and Max HP, or Gold.  File->Save.  Go back to STS and "Continue".  If all goes well you'll see your change.  If all goes badly.. well, karma?  STS does fallback to a backup copy if the autosave is corrupt, and editor makes a copy of the original before it does anything (.autosave.1) so it is at least somewhat safe.

Potions are not done yet, but Cards and Relics can be added/removed.  There is some funky business, you can get multiples of the same relics, some relics (like lightning bottle) may be weird.  Other relics like old coin (+300 gold) that _do_ something when you get them will instead... do nothing.

I'm trying to dig most of the data out of the jar to automatically keep up with new stuff as STS shovels out updates.  This should work for most things.  Right now new settings or metrics won't show up.  New other-stuff is likely to just work.

## The Good:

- [x] Opening .autosave files works
- [x] Parsing STS .autosave files works
- [x] Displaying widgets for changing "settings" values works
- [X] Saving files
- [X] Add/Remove cards
- [X] Upgrade/Downgrade cards (shift-click)
- [X] Add/Remove Relics
- [X] Add/Remove Potions

## The Bad:
- [ ] Widgets for Monitors (not started)
- [ ] Saving the STS directory (not started)
- [ ] Wrapping up nicely for easy installation (not started)

## Building Win Installable

pip install py2exe
python setup.py py2exe

https://jrsoftware.org/isinfo.php


## Other STS editors:

  https://gira-x.github.io/save-the-spire/
