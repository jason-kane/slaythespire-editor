# Save The Spire Savefile Editor

Python/wxPython based.

## Getting Started

Put editor.py in a subdirctory of SaveTheSprire, it doesn't matter what the name is.  You could put it in the /save directory.

* pip install -U wxPython Krakatau-noff
* python3 ./editor.py

## But.. how do I _use_ it?
Start a game.  At any time after the first group, save and exit to the main screen.  Run editor.py, File->Load the .autosave for your character.  Change whatever you want.  Maybe HP and Max HP, or Gold.  File->Save.  Go back to STS and "Continue".  If all goes well you'll see your change.  If all goes badly.. well, karma?  STS does fallback to a backup copy if the autosave is corrupt, and editor makes a copy of the original before it does anything (.autosave.1) so its at least mostly safe.

Editing cards, potions and artifacts aren't written yet.  I know, that is what you really want to mess with.  Sorry.  I'll get to them.  It is also possible I will abandon this little project and forget all about it. :shrug:

I'm trying to dig most of the data out of the jar to keep up with new stuff as STS shovels out updates.  This should work for minor stuff (new cards, potions, etc..) but if they add more colors/characters it will probably still take a code update.

## The Good:

- [x] Opening .autosave files works
- [x] Parsing STS .autosave files works
- [x] Displaying widgets for changing "settings" values works
- [X] Saving files

## The Bad:


- [ ] Widgets for Cards (not started)
- [ ] Widgets for Artifacts (not started)
- [ ] Widgets for Potions (not started)
- [ ] Widgets for Monitors (not started)
- [ ] Saving the STS directory (not started)
- [ ] Wrapping up nicely for easy installation (not started)


If you want something that actually mostly works:

  https://gira-x.github.io/save-the-spire/
