import editor

ss = editor.SlaySave()

decoded = ss.load_file('DEFECT.autosave')

with open('DEFECT.autosave.baked', 'w') as h:
	for d in decoded:
		h.write(f"{d}: {decoded[d]}")

with open('DEFECT.autosave.decoded', 'w') as h:
	h.write(ss.as_str(decoded))

# print("-"*60)

# decoded["gold"] = str(int(decoded["gold"] * 2))
# ss.save_file("DEFECT.autosave.1", decoded)


print("-"*60)
decoded = ss.load_file('DEFECT.autosave.1')
with open('DEFECT.autosave.1.baked', 'w') as h:
	for d in decoded:
		h.write(f"{d}: {decoded[d]}")

with open('DEFECT.autosave.1.decoded', 'w') as h:
	h.write(ss.as_str(decoded))


