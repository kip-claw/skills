import sys, json
d = json.load(sys.stdin)
download = round(d['download'] / 1_000_000, 2)
upload   = round(d['upload']   / 1_000_000, 2)
ping     = round(d['ping'], 1)
server   = d['server']['name'].strip().replace('\n', ' ').replace(',', '')
sponsor  = d['server']['sponsor'].strip().replace('\n', ' ').replace(',', '')
print(f"{download}|{upload}|{ping}|{server}|{sponsor}")
