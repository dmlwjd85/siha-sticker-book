"""Round 9: the right side strand of hair_front got a tone break/gap (part ~x880,y372) from earlier
edits. HEAD (qa9/orig) had a clean gradient there, so blend HEAD pixels back in with a feathered box."""
import sys, numpy as np, cv2
from PIL import Image
P = sys.argv[1] if len(sys.argv) > 1 else 'public/v3-demo/parts'
SRC = '/workspace/qa9/orig/hair_front.png'
f = f'{P}/hair_front.png'
A = np.array(Image.open(f).convert('RGBA')).astype(float)
B = np.array(Image.open(SRC).convert('RGBA')).astype(float)
w = np.zeros(A.shape[:2], np.float32); w[300:440, 855:905] = 1
w = cv2.GaussianBlur(w, (0, 0), 5)[..., None]
A = A * (1 - w) + B * w
Image.fromarray(np.clip(A + .5, 0, 255).astype(np.uint8)).save(f)
print('strand blend ok')
