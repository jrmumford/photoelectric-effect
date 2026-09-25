import math, sys
from PIL import Image, ImageDraw, ImageFilter
N=1024
bg=Image.new("RGBA",(N,N)); d=ImageDraw.Draw(bg)
for y in range(N):
    t=y/N; d.line([(0,y),(N,y)],fill=(int(16+22*t),int(26+34*t),int(58+56*t),255))
mask=Image.new("L",(N,N),0); ImageDraw.Draw(mask).rounded_rectangle([60,60,N-60,N-60],radius=200,fill=255)
img=Image.new("RGBA",(N,N),(0,0,0,0)); img.paste(bg,(0,0),mask)
d=ImageDraw.Draw(img)
# metal plate
d.rounded_rectangle([680,220,770,810],radius=20,fill=(178,186,198,255),outline=(228,233,240,255),width=8)
# photon: smooth sine drawn as overlapping discs, red -> violet
cols=[(255,70,60),(255,160,20),(250,220,40),(60,220,90),(70,130,255),(185,85,255)]
def col(t):
    i=min(int(t*(len(cols)-1)),len(cols)-2); f=t*(len(cols)-1)-i
    return tuple(int(cols[i][k]*(1-f)+cols[i+1][k]*f) for k in range(3))+(255,)
x0,x1,yc,amp,r=150,560,590,58,17
M=1600
for s in range(M+1):
    t=s/M; x=x0+(x1-x0)*t; y=yc+amp*math.sin(t*3.5*2*math.pi)*(1-0.15*t)
    d.ellipse([x-r,y-r,x+r,y+r],fill=col(t))
yend=yc+amp*math.sin(3.5*2*math.pi)*0.85
d.line([(x1,yend),(600,yc)],fill=col(1),width=2*r)
d.polygon([(672,yc),(596,yc-48),(596,yc+48)],fill=col(1))
# ejected electron
ex,ey=440,300
glow=Image.new("RGBA",(N,N),(0,0,0,0)); ImageDraw.Draw(glow).ellipse([ex-95,ey-95,ex+95,ey+95],fill=(120,200,255,170))
img=Image.alpha_composite(img,glow.filter(ImageFilter.GaussianBlur(32))); d=ImageDraw.Draw(img)
ang=math.atan2(ey-520,ex-675)  # direction of travel: away from the plate
ux,uy=math.cos(ang),math.sin(ang); px,py=-uy,ux
for off,ln in ((0,150),(-38,105),(38,105)):
    sx,sy=ex-ux*80+px*off, ey-uy*80+py*off
    d.line([(sx,sy),(sx-ux*ln,sy-uy*ln)],fill=(165,212,255,210),width=14)
R=62
d.ellipse([ex-R,ey-R,ex+R,ey+R],fill=(88,172,255,255),outline=(232,246,255,255),width=10)
d.rounded_rectangle([ex-30,ey-8,ex+30,ey+8],radius=6,fill=(255,255,255,255))
img.save(sys.argv[1])
