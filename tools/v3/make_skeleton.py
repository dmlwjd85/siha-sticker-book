"""parts.json → skeleton.json (Spine 비슷한 뼈·슬롯·스킨·옷·움직임). 좌표는 2배 캔버스(1440x2560), y 아래로."""
import json, sys, os
from build_v3 import CUT, GRIP, ELBOW_R, WAVE_PIVOT, WAVE_ANGLES, S
OUT=sys.argv[1] if len(sys.argv)>1 else 'out'
P=json.load(open(f'{OUT}/parts.json'))
s2=lambda p:{'x':p[0]*S,'y':p[1]*S}
bones=[('root',None,(360,CUT)),('pelvis','root',(360,CUT)),('chest','pelvis',(360,CUT)),('neck','chest',(360,330)),('head','neck',(360,300)),
 ('upperarm_r','chest',(275,370)),('forearm_r','upperarm_r',ELBOW_R),('hand_r','forearm_r',GRIP),('prop_r','hand_r',GRIP),
 ('upperarm_l','chest',(445,370)),('forearm_l','upperarm_l',WAVE_PIVOT),('hand_l','forearm_l',(530,300))]
sk={'skeleton':{'spine':'4.2-like','width':1440,'height':2560,'scale':S,'stagePad':160,
   'note':'y 아래로. 원본 720x1280 그림을 2배로 다듬음. 기본 자세 = 한 손 마이크(주먹 안 소품 슬롯 prop_r), 다른 손 아래로 가볍게 쥠'},
 'bones':[{'name':n,**({'parent':p} if p else {}),'rest':s2(r)} for n,p,r in bones],
 'slots':[{'name':'hair_back','bone':'head','attachment':'hair_back'},
   {'name':'body_lower','bone':'pelvis','attachment':'body_lower'},{'name':'fit_lower','bone':'pelvis'},
   {'name':'body_upper','bone':'chest','attachment':'body_upper'},{'name':'fit_upper','bone':'chest'},
   {'name':'wave_arm','bone':'chest'},{'name':'eyes','bone':'head'},{'name':'hair_front','bone':'head','attachment':'hair_front'},
   {'name':'prop','bone':'prop_r','attachment':'mic'},{'name':'hand_r','bone':'hand_r','attachment':'hand_r'}],
 'skins':[{'name':'default','attachments':{
   'hair_back':{'hair_back':P['hair_back'],'hair_back_wave':P['hair_back_wave']},'hair_front':{'hair_front':P['hair_front']},
   'body_lower':{'body_lower':P['pelvis'],'body_lower_wave':P['pelvis_wave']},
   'body_upper':{'body_upper':P['chest'],'body_upper_wave':P['chest_wave']},
   'fit_lower':{'basic_lower':P['basic_pelvis'],'basic_lower_wave':P['basic_pelvis_wave']},
   'fit_upper':{'basic_upper':P['basic_chest'],'basic_upper_wave':P['basic_chest_wave']},
   'eyes':{'eyes_closed':P['eyes_closed']},'hand_r':{'hand_r':P['hand_r']},
   'prop':{'mic':{'path':'parts/prop_mic.png','grip':0.5,'scale':0.2,'rotation':-8}},
 }}],
 'outfits':{'basic':{'fit_lower':'basic_lower','fit_upper':'basic_upper','wave':{'fit_lower':'basic_lower_wave','fit_upper':'basic_upper_wave'}}},
 'props':{'mic':{'slot':'prop','bone':'prop_r','note':'손잡이 가운데(grip)를 주먹 가운데에 둔다. 주먹·아래팔 조각(hand_r)이 그 위에 그려져 손잡이를 가린다'}},
 'animations':{
   'blink':{'period':4.2,'slots':{'eyes':{'attachment':[{'time':0,'name':None},{'time':3.95,'name':'eyes_closed'},{'time':4.1,'name':None}]}}},
   'breathe':{'period':3.2,'bones':{'chest':{'scale':[{'time':0,'y':1},{'time':1.6,'y':1.006},{'time':3.2,'y':1}]}}},
   'wave':{'period':1.6,'repeat':2,'swap':{'hair_back':'hair_back_wave','body_lower':'body_lower_wave','body_upper':'body_upper_wave'},
     'frames':[{'angle':f['angle'],'body':f['body'],'basic':f['basic']} for f in P['wave_frames']],
     'angle':[{'time':0,'value':0},{'time':0.4,'value':10},{'time':0.8,'value':-10},{'time':1.2,'value':10},{'time':1.6,'value':0}]},
   'mic_bob':{'period':3.2,'note':'숨쉬기와 같이 주먹·마이크가 가슴 뼈를 따라 살짝 오르내림(따로 키 없음)'}},
 'accessories':[{'name':'acc_ribbon','path':'parts/acc_ribbon.png'},{'name':'acc_star','path':'parts/acc_star.png'}]}
from PIL import Image
for a in sk['accessories']:
    w,h=Image.open(f"{OUT}/{a['path']}").size; a['width'],a['height']=w,h
m=Image.open(f'{OUT}/parts/prop_mic.png'); fh=json.load(open(f'{OUT}/mic_meta.json'))['full_h']
sk['skins'][0]['attachments']['prop']['mic'].update(width=m.width,height=m.height,grip=round(0.5*fh/m.height,4))   # grip = 잘린 그림 높이 기준 손잡이 가운데
wm=json.load(open(f'{OUT}/wave_meta.json'))['wave_change_box']; from build_v3 import WAVE_BOX
sk['animations']['wave']['changeBox']=[min(wm[0],WAVE_BOX[0])*S,min(wm[1],WAVE_BOX[1])*S,max(wm[2],WAVE_BOX[2])*S,max(wm[3],WAVE_BOX[3])*S]   # 흔들기 때 바뀌어도 되는 곳(검사용)
json.dump(sk,open(f'{OUT}/skeleton.json','w'),ensure_ascii=False,indent=1); print('skeleton ok')
