cd /workspace/ssb && python3 /workspace/qa11/r13/setpose.py $1 $2 $3 >/dev/null && npx vite build >/tmp/vb.log 2>&1 && node /workspace/pw/one.mjs /workspace/qa11/r13/$4 >/dev/null && python3 -c "
from PIL import Image
im=Image.open('/workspace/qa11/r13/$4_none_idle.png'); im.crop((220,330,500,640)).resize((560,620)).save('/tmp/$4n.png')"
