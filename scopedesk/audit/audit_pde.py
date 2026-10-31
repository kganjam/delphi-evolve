import numpy as np
def run(alpha,T=120.0,L=500.0,dx=0.25,dt=0.02):
    x=np.arange(0,L,dx); u=np.where(x<5,1.0,0.0); n=int(T/dt); pos=[]
    for k in range(n):
        lap=np.empty_like(u); lap[1:-1]=u[2:]-2*u[1:-1]+u[:-2]; lap[0]=u[1]-u[0]; lap[-1]=u[-2]-u[-1]
        u=u+dt*(lap/dx**2+u*(1-u)*(1+alpha*u))
        if k%int(1/dt)==0: pos.append(x[np.argmax(u<0.5)])
    pos=np.array(pos); t=np.arange(len(pos))
    sel=(t>=60)
    return np.polyfit(t[sel],pos[sel],1)[0]
for a in (0.0,5/3,2.0,4.0,10/3):
    pred=2 if a<=2 else (2+a)/np.sqrt(2*a)
    print(a,'measured',round(run(a),3),'theory',round(pred,3),'(2.0 = KPP)')
