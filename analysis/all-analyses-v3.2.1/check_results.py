#!/usr/bin/env python3
"""Independent arithmetic checks and manuscript-facing comparisons of frozen results."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent;P=ROOT/'results'
def load(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
A=load(P/'analyses.json');D=load(P/'delta/delta_results.json');checks=load(P/'checks.json')
for old in load(ROOT/'inputs/old_readability.json'):
 r=next(r for r in A['legacy']['rows'] if r['witness']==old['stem'])
 reg='pref' if old['Typ']=='Vorwort' else 'diary'
 for new,prev in [('flesch','Flesch'),('coleman_liau','Coleman_Liau')]:assert abs(r['metrics'][reg][new]-float(old[prev]))<1e-10
checks['legacy_readability_36_values_match_archive']=True
for old,r in zip(load(ROOT/'inputs/old_lexicometrics.json'),A['legacy']['rows']):
 f=r['metrics']['full'];assert f['whitespace_units']==int(old['word_count'])
 for new,prev in [('words_per_sentence','mean_sentence_length'),('characters_per_word','mean_word_length_chars'),('syllables_per_word','mean_syllables_per_word')]:assert round(f[new],3)==float(old[prev])
checks['legacy_lexical_36_values_match_archive']=True
checks['legacy_exclusivity_9_values_match_manuscript']=[r['exclusive_count'] for r in A['legacy']['rows']]==[6,353,4,15,70,279,2,287,7]
assert checks['legacy_exclusivity_9_values_match_manuscript']
# Cross-language verification: recreate Delta from the frequency tables with NumPy.
delta_errors=[]
for key,track in D['analyses'].items():
 # R writes a whitespace-separated frequency table; the first column is the row name.
 lines=(P/'delta'/key/'table_with_frequencies.txt').read_text().splitlines()
 import csv,io
 # Tabs retain quoted names and an empty top-left field.
 data=list(csv.reader(lines,delimiter='\t'))
 if len(data[0])==1:
  import shlex
  data=[shlex.split(x) for x in lines]
 names=data[0]; rows=data[1:]
 features=[r[0] for r in rows];freq=np.array([[float(x) for x in r[1:]] for r in rows]).T
 for m,level in track['levels'].items():
  x=freq[:,[features.index(f) for f in level['features']]]
  x=x[[names.index(n) for n in level['witnesses']]]
  z=(x-x.mean(axis=0))/x.std(axis=0,ddof=1)
  d=np.abs(z[:,None,:]-z[None,:,:]).mean(axis=2)
  error=float(np.max(np.abs(d-np.array(level['matrix']))));delta_errors.append(error)
  assert error<1e-8,(key,m,error)
checks['delta_25_matrices_numpy_vs_stylo_max_abs_error']=max(delta_errors)
checks['consensus_topology_same_across_three_full_text_tracks']=len({D['analyses'][t+'_full']['consensus_newick'] for t in A})==1
rows=A['corrected']['rows'];syn=load(ROOT/'inputs/syntax_full.json')
sentence_rows=load(ROOT/'inputs/sentences.json')
table=[]
for i,r in enumerate(rows):
 assert r['witness']==syn[i]['witness']
 assert r['metrics']['full']['sentences']==syn[i]['sentences']
 ss=[s for s in sentence_rows if s['witness']==r['witness']]
 assert sum(len(s['clauses']) for s in ss)==syn[i]['clauses']
 assert abs(sum(s['depth_reviewed'] for s in ss)/len(ss)-syn[i]['depth_reviewed'])<1e-12
 table.append(dict(witness=r['witness'],label=r['label'],**r['metrics']['full'],subordination_index=syn[i]['index'],dependency_depth=syn[i]['depth_reviewed']))
save(P/'table2.json',table)
claims={
 'all_prefaces_lower_flesch':all(r['metrics']['pref']['flesch']<r['metrics']['diary']['flesch'] for r in rows),
 'all_prefaces_higher_coleman_liau':all(r['metrics']['pref']['coleman_liau']>r['metrics']['diary']['coleman_liau'] for r in rows),
 'flesch_gap_descending':[r['label'] for r in sorted(rows,key=lambda r:r['metrics']['diary']['flesch']-r['metrics']['pref']['flesch'],reverse=True)],
 'coleman_liau_gap_descending':[r['label'] for r in sorted(rows,key=lambda r:r['metrics']['pref']['coleman_liau']-r['metrics']['diary']['coleman_liau'],reverse=True)],
 'motif_counts_unchanged':all(r['motif']==A['legacy']['rows'][i]['motif'] for i,r in enumerate(rows)),
 'pca_wordform_percent':A['corrected']['pca_wordform']['explained_percent'],
 'herzfeldt_full_nearest_by_mfw':{m:next(x for x in lev['nearest'] if 'Herzfeldt' in x['witness']) for m,lev in D['analyses']['corrected_full']['levels'].items()},
 'pengkun_full_nearest_by_mfw':{m:next(x for x in lev['nearest'] if 'Pengkun' in x['witness']) for m,lev in D['analyses']['corrected_full']['levels'].items()}}
save(P/'interpretation_checks.json',claims)
comparison=[]
for i,r in enumerate(rows):
 old=A['legacy']['rows'][i];repair=A['repairs_only']['rows'][i]
 comparison.append(dict(witness=r['witness'],label=r['label'],legacy=old['metrics'],repairs_only=repair['metrics'],corrected=r['metrics'],
    exclusive_counts={k:A[k]['rows'][i]['exclusive_count'] for k in A},
    exclusive_removed=sorted(set(old['exclusive_types'])-set(r['exclusive_types'])),exclusive_added=sorted(set(r['exclusive_types'])-set(old['exclusive_types']))))
printed=load(ROOT/'inputs/manuscript_table2_before_recalculation.json')
for item,old in zip(comparison,printed[1:]):item['previous_manuscript_table2_display']=dict(zip(printed[0],old))
save(P/'comparison.json',comparison)
checks['syntax_aggregates_verified_from_2404_sentences']=True
save(P/'checks.json',checks)
# Fresh ±7-token concordances preserve punctuation in the surrounding source string.
import re
kwic=[]
for row in rows:
 text=(P/'corpora/corrected/full'/f"{row['witness']}.txt").read_text()
 matches=list(re.finditer(r"\b[\wäöüß'-]+\b",text,re.I))
 for field in row['motif']:
  hits=[]
  for i,m in enumerate(matches):
   if field in m.group().lower():
    lo=matches[max(0,i-7)].start();hi=matches[min(len(matches)-1,i+7)].end()
    hits.append(dict(word_index=i+1,match=m.group(),left=text[lo:m.start()],right=text[m.end():hi]))
  assert len(hits)==row['motif'][field]
  kwic.append(dict(witness=row['witness'],field=field,hits=hits))
save(P/'kwic.json',kwic)
manifest=load(P/'manifest.json');manifest['input_sha256']={str(p.relative_to(ROOT/'inputs')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'inputs').rglob('*')) if p.is_file()};save(P/'manifest.json',manifest)
print(json.dumps(checks,indent=2));print(json.dumps(claims,ensure_ascii=False,indent=2))
