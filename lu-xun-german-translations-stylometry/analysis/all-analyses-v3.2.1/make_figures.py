#!/usr/bin/env python3
"""Publication figures from the corrected v3.2.1 numerical results."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'figures';OUT.mkdir(exist_ok=True)
R=json.loads((ROOT/'results/analyses.json').read_text())['corrected']
H=json.loads((ROOT/'results/historical_markedness.json').read_text())
LABELS=[r['label'] for r in R['rows']]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,
 'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
COLORS=['#164d70','#8d391f','#164d70','#164d70','#3d6845','#8d391f','#3d6845','#672d75','#3d6845']

def finish(fig,stem):
    fig.savefig(OUT/(stem+'.png'),dpi=300,bbox_inches='tight',facecolor='white',metadata={})
    fig.savefig(OUT/(stem+'.pdf'),bbox_inches='tight',metadata={'Creator':None,'Producer':None,'CreationDate':None,'ModDate':None})
    im=Image.open(OUT/(stem+'.png'));im.load();im.save(OUT/(stem+'.png'))
    plt.close(fig)

# PCA: leader lines disambiguate nearly coincident witnesses without moving observations.
fig,ax=plt.subplots(figsize=(8,5.4));xy=np.array(R['pca_wordform']['coordinates'])
offsets=[(24,-24),(12,8),(24,10),(-70,21),(-17,30),(-82,-13),(-70,-20),(12,-12),(-7,-36)]
for i,((x,y),off) in enumerate(zip(xy,offsets)):
    ax.scatter(x,y,c=COLORS[i],s=45,zorder=4)
    ax.annotate(LABELS[i],(x,y),xytext=off,textcoords='offset points',fontsize=10,
                arrowprops={'arrowstyle':'-','lw':.6,'color':'.4'})
ax.set_xlim(-.27,.32);ax.set_ylim(-.16,.20)
ev=R['pca_wordform']['explained_percent']
ax.set_xlabel(f'PC1 ({ev[0]:.2f}%)');ax.set_ylabel(f'PC2 ({ev[1]:.2f}%)')
ax.grid(alpha=.2);fig.tight_layout();finish(fig,'Fig01_PCA')

# Readability: numeric labels identify overlapping points via a compact key.
fig,ax=plt.subplots(figsize=(8,5.7))
poff=[(-40,12),(7,8),(-40,-18),(-42,-35),(-50,-24),(5,8),(15,10),(7,8),(15,-12)]
doff=[(-65,-4),(8,4),(-53,15),(-20,18),(-51,0),(12,28),(10,14),(10,-24),(12,-5)]
for i,r in enumerate(R['rows']):
    p=r['metrics']['pref'];d=r['metrics']['diary'];a=(p['flesch'],p['coleman_liau']);b=(d['flesch'],d['coleman_liau'])
    ax.plot([a[0],b[0]],[a[1],b[1]],c=COLORS[i],lw=.65,alpha=.5)
    ax.scatter(*a,marker='o',s=42,facecolors='white',edgecolors=COLORS[i],zorder=4)
    ax.scatter(*b,marker='+',s=65,c=COLORS[i],zorder=4)
    for point,off in [(a,poff[i]),(b,doff[i])]:
        ax.annotate(str(i+1),point,xytext=off,textcoords='offset points',fontsize=10,
                    arrowprops={'arrowstyle':'-','lw':.5,'color':'.5'})
ax.set_xlim(41.8,72);ax.set_ylim(10.4,14.9)
ax.set_xlabel('Flesch Reading Ease (Amstad; higher = easier)')
ax.set_ylabel('Coleman–Liau, unadapted (higher = harder)')
ax.plot([],[],marker='o',mfc='white',color='.2',ls='',label='Preface')
ax.plot([],[],marker='+',color='.2',ls='',label='Diary')
ax.legend(loc='upper right',frameon=False,ncol=2,fontsize=10)
ax.grid(alpha=.15)
fig.subplots_adjust(bottom=.29,left=.12,right=.98,top=.97)
for i,label in enumerate(LABELS):
    fig.text(.12+(i%3)*.30,.16-(i//3)*.043,f'{i+1}  {label}',fontsize=9.5)
finish(fig,'Fig03_Readability')

# Markedness keeps the existing contextual classification; only occurrences and denominators are checked anew.
terms=list(dict.fromkeys(e['term'] for r in H for e in r['evidence']))
fig,ax=plt.subplots(figsize=(8,4.9))
for i,r in enumerate(H):
    for e in r['evidence']:
        j=terms.index(e['term']);n=e['annotated_tokens']
        ax.scatter(i,j,s=85*n,facecolors='#526c80',edgecolors='white',linewidths=.5)
        ax.text(i,j,str(n),ha='center',va='center',color='white',fontsize=9)
ax.set_xticks(range(9),LABELS,rotation=45,ha='right',fontsize=9)
ax.set_yticks(range(len(terms)),terms,fontsize=10)
ax.set_xlim(-.7,8.7);ax.set_ylim(-.8,len(terms)-.2);ax.invert_yaxis()
ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True);fig.tight_layout();finish(fig,'Fig04_Historical_Markedness')

fig,ax=plt.subplots(figsize=(8,5.2));v=[r['exclusive_count'] for r in R['rows']]
bars=ax.barh(range(9),v,color=COLORS,height=.65)
ax.set_yticks(range(9),LABELS,fontsize=11);ax.invert_yaxis();ax.set_xlim(0,max(v)*1.15)
for i,n in enumerate(v):ax.text(n+4,i,str(n),va='center',fontsize=11)
ax.set_xlabel('Witness-exclusive word types');ax.grid(axis='x',alpha=.17);ax.set_axisbelow(True)
fig.tight_layout();finish(fig,'Fig05_Exclusive_Words')

fields=list(R['rows'][0]['motif'])
mat=np.array([[r['motif'][f] for f in fields] for r in R['rows']])
fig,ax=plt.subplots(figsize=(8,5.1));ax.imshow(mat,cmap='Blues',aspect='auto',vmin=0,vmax=mat.max())
for i in range(9):
    for j in range(len(fields)):ax.text(j,i,str(mat[i,j]),ha='center',va='center',color='white' if mat[i,j]>mat.max()*.55 else 'black',fontsize=10)
ax.set_xticks(range(len(fields)),fields,rotation=45,ha='right',fontsize=10)
ax.set_yticks(range(9),LABELS,fontsize=10)
ax.set_xlabel('Word-form substring (overlapping categories)');fig.tight_layout();finish(fig,'Fig06_Motif')
