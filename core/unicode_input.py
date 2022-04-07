import IPython.core.completer as completer

unicode_input = dict()

with open("unicode_input") as src:
    while True:
        l = src.readline()
        if len(l) == 0:
            break
        items = l.split("\t")
        if len(items) != 4:
            break
        if "tab completion sequence" in items[2].lower():
            continue
        unicode_input[items[2]]=items[1]

for k,i in unicode_input.items():
    if k not in completer.latex_symbols:
        latex_symbols[k]=i
