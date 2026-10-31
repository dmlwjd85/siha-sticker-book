import json,sys;from PIL import Image
P='/workspace/ssb/public/v4c-demo/';sk=json.load(open(P+'skeleton.json'))
items=sys.argv[1].split(',') if len(sys.argv)>1 else []
sl=sk.get('slots') or sk.get('parts')
c=Image.new('RGBA',(1440,2560),(255,0,255,255))
for s in (sl if isinstance(sl,list) else sl.values()):
    if s.get('item') and s['item'] not in items: continue
    c.alpha_composite(Image.open(P+s['path']).convert('RGBA'),(s['x'],s['y']))
c.save(sys.argv[2] if len(sys.argv)>2 else 'zz/comp.png')
