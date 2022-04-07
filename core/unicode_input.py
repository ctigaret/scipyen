
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

