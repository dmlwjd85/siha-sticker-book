import json,sys
p='/workspace/ssb/public/v3-demo/skeleton.json'; S=open(p).read()
s=json.loads(S); old=json.dumps(s['restPose'])
tx,ty,rot=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3])
fr={'rotate':rot}
if tx or ty: fr.update(x=tx,y=ty)
s['restPose']['forearm_r']=fr
import re
i=S.index('"restPose"'); j=S.index('}',S.index('}',i)+1)+1
new='"restPose": '+json.dumps(s['restPose'])
S2=S[:i]+new+S[j:]
json.loads(S2); open(p,'w').write(S2); print(S2[i-5:i+len(new)+20])
