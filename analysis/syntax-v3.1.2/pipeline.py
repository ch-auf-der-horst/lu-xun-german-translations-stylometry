"""Versioned syntax reanalysis. No writes to source corpus/manuscript.

Primary SI: explicitly introduced finite clause heads, one per verb complex.
Dependency depth: maximum edge count per orthographic sentence, root depth 0;
arithmetic sentence mean. Auxiliary contraction is diagnostic only.
"""
from pathlib import Path
import argparse, json, hashlib, re, unicodedata, statistics, ast
import spacy
from spacy.language import Language

VERSION='3.1.2'
ROOT=Path(__file__).resolve().parent
INTRO={'dass','daß','sodass','weil','ob','obwohl','obgleich','obschon','wiewohl','wenn','falls','sofern','sobald','solange','sooft','seitdem','nachdem','bevor','ehe','bis','während','indem','damit','als','seit','da','je'}
W_TAG={'PWS','PWAT','PWAV','PRELS','PRELAT'}
VERB_TAG=re.compile(r'^V[AVM](?:FIN|INF|IZU|PP|IMP)$')
REPORT={'sagte','fragte','erwiderte','antwortete','rief','dachte','murmelte','schrie','brüllte','flüsterte','fuhr'}

def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def normalize(raw,reg,witness=None):
    """Preserve a character-level provenance map to the original register."""
    text=raw;mapping=list(range(len(raw)));events=[]
    def replace(pattern,repl,label,flags=0):
        nonlocal text,mapping
        hits=list(re.finditer(pattern,text,flags))
        for m in reversed(hits):
            old=m.group();new=repl(m) if callable(repl) else repl
            origin=mapping[m.start():m.end()]
            events.append({'rule':label,'source_start':min(origin) if origin else None,'source_end':max(origin)+1 if origin else None,'before':old,'after':new})
            nm=[origin[min(int(i*len(origin)/max(len(new),1)),len(origin)-1)] for i in range(len(new))] if origin else []
            text=text[:m.start()]+new+text[m.end():];mapping=mapping[:m.start()]+nm+mapping[m.end():]
    if reg=='pref':
        replace(r'^\s*(?:Das )?Tagebuch (?:eines|des) (?:Verrückten|Wahnsinnigen|Verstörten)\.\s*','','remove_title')
        replace(r'\s*(?:(?:Aufgezeichnet|Geschrieben) am )?2\.\s*April\s*(?:1918|im 7\. Jahr der Republik)\.?\s*$','','remove_pref_date')
    else:
        replace(r'\s*(?:April\s+)?1918\.?\s*$','','remove_diary_date')
    replace(r'\{\*chin\*\}','Chin','name_placeholder')
    # Orthographic normalization is confined to the analysis copy, fully logged.
    replace(r'\bsodass\b','so dass','normalize_so_dass',re.I)
    # Editorial repairs of the four user-flagged passages; applied wherever exact
    # same surface occurs, never to the immutable source files.
    replace(r'\bV erfasset\b','Verfasser','editorial_verfasser')
    replace(r'\bV ersuch\b','Versuch','join_versuch')
    replace(r"\bauf' geschlossen\b",'aufgeschlossen','join_aufgeschlossen')
    replace(r'einlegte, Wie soll ich nun','einlegte. Wie soll ich nun','restore_sentence_boundary_after_einlegte')
    # Source-confirmed OCR repair, restricted to the Pengkun diary (print p. 13).
    if witness=='2019_Pengkun_cleaned' and reg=='diary':
        replace(r'\bGläubigem\b','Gläubigern','restore_glaeubigern_pengkun_2019')
    replace(r'\s+',' ','whitespace')
    a=len(text)-len(text.lstrip());b=len(text.rstrip());text=text[a:b];mapping=mapping[a:b]
    if not text:raise ValueError('Empty register after normalization')
    if '{*' in text or '*}' in text:raise ValueError('Unresolved placeholder markup')
    return text,mapping,sorted(events,key=lambda e:e['source_start'] or 0)

@Language.component('lu_xun_boundaries')
def boundaries(doc):
    for t in doc:t.is_sent_start=False
    if len(doc):doc[0].is_sent_start=True
    level=0
    for i,t in enumerate(doc[:-1]):
        if t.text in {'(','['}:level+=1
        elif t.text in {')',']'}:level=max(0,level-1)
        if level or t.text not in {'.','!','?','…','...'}:continue
        # Punctuation runs belong together; colon and semicolon do not end a sentence.
        nxt=doc[i+1]
        if nxt.text in {'.','!','?','…','...',',',';',':',')',']','”','“','"','»','«','’'}:continue
        if nxt.lower_ in REPORT:continue
        if nxt.text[:1].islower():continue
        # Numbered dates are stripped, but surviving ordinal punctuation stays internal.
        if t.text=='.' and i>0 and doc[i-1].like_num:continue
        nxt.is_sent_start=True
    return doc

def verbish(t):return t.pos_ in {'VERB','AUX'} or (t.pos_ not in {'DET','PRON','ADP','SCONJ','CCONJ','PART','PUNCT'} and bool(VERB_TAG.match(t.tag_)))
def finite(t):return verbish(t) and ('Fin' in t.morph.get('VerbForm') or t.tag_.endswith('FIN'))

def verbal_cluster(t):
    """Head plus nonfinite verbal dependents, never across finite-clause boundaries."""
    seen={t.i};out=[t];queue=[t]
    while queue:
        h=queue.pop()
        for c in h.children:
            if c.i not in seen and verbish(c) and not finite(c) and c.dep_ in {'oc','pd'}:
                seen.add(c.i);out.append(c);queue.append(c)
    return out

def finite_head_candidate(t):
    if finite(t):return True,'finite_feature_or_tag'
    # Constrained rescue: parser has a verbal predicate, a subject and a clause cue,
    # but mistags an ambiguous finite surface as participle/infinitive.
    if not verbish(t):return False,''
    children=list(t.children)
    cue=t.dep_=='rc' or any(c.dep_=='cp' and c.lower_ in INTRO for c in children)
    subject=any(c.dep_=='sb' for c in children)
    aux_governor=verbish(t.head) and t.head!=t and t.dep_ in {'oc','pd'} and finite(t.head)
    lemma=t.lemma_.lower();stem=lemma[:-2] if lemma.endswith('en') else lemma[:-1] if lemma.endswith('n') else lemma
    plausible=t.lower_ in {stem+x for x in ['e','st','t','en','et','est']} or t.lower_ in {'können','müssen','dürfen','wollen','sollen','mögen','haben','werden','troffen'}
    if cue and subject and plausible and not aux_governor and not any(finite(c) and c.dep_ in {'oc','pd'} for c in children):return True,'finite_rescue'
    return False,''

def has_local_w(t,c,doc):
    """Require a subordinate parse and left-positioned w/relative constituent.
    No global verb-final requirement: extraposed infinitives/PPs are allowed.
    """
    if t.dep_ not in {'oc','mo','re','sb','oa','pd','rc','cj'} or t.dep_=='ROOT':return False
    if c.i>=t.i:return False
    subjects=[s for s in t.children if s.dep_=='sb']
    if subjects and all(s.i>t.i for s in subjects):return False
    if t.dep_=='cj' and c.tag_ in {'PRELS','PRELAT'} and any(s.dep_ in {'oa','da','og'} and s.i>t.i for s in t.children):return False
    if t.head.i<c.i and any(x.text==':' for x in doc[t.head.i:c.i]):return False
    if t.i<t.head.i and any(x.text in {'?','!'} for x in doc[t.i:t.head.i]):return False
    # W-tag may be on a determiner within a PP/NP, not directly on the predicate.
    return c.tag_ in W_TAG

def detect_clauses(doc):
    out={};review=[]
    for t in doc:
        ok,how=finite_head_candidate(t)
        if not ok:continue
        cluster=verbal_cluster(t);ids={x.i for x in cluster}
        children=[c for x in cluster for c in x.children if c.i not in ids]
        cue=None;reason=None
        if t.dep_=='rc':reason='relative';cue=next((c for c in children if c.tag_ in W_TAG),None)
        if reason is None:
            cue=next((c for c in children if c.dep_=='cp' and c.lower_ in INTRO),None)
            if cue is not None:reason='subordinator_via_verb_complex'
        if reason is None:
            cue=next((c for c in children if c.lower_=='als' and c.dep_=='cm' and c.pos_ in {'SCONJ','CCONJ','ADP'}),None)
            if cue is not None:reason='als_comparison'
        if reason is None:
            # Climb only through non-verbal constituents owned by this verb complex.
            candidates=[]
            for c in children:
                candidates.append(c)
                if not verbish(c):
                    candidates += [d for d in c.subtree if all(not verbish(a) for a in d.ancestors if a.i!=t.i and a.i not in ids and a.i>=c.left_edge.i and a.i<=c.right_edge.i)]
            cue=next((c for c in candidates if has_local_w(t,c,doc)),None)
            if cue is not None:reason='w_or_free_relative'
        if reason is None:
            # je ... desto and so ADJ ... finite predicate (concessive) are not cp.
            cue=next((d for c in children if not verbish(c) for d in c.subtree if d.lower_=='je'),None)
            if cue is not None and t.dep_ in {'cc','mo','re','oc'}:reason='je_comparison'
        if reason is None:
            cue=next((d for c in children if c.tag_=='ADJD' for d in c.subtree if d.lower_=='so'),None)
            if cue is not None and t.dep_ in {'mo','re'} and t.i<t.head.i and any(c.dep_=='sb' or c.dep_=='ep' for c in children):reason='so_concessive'
        if reason:
            out[t.i]={'i':t.i,'text':t.text,'kind':'I','rule':reason,'finite_evidence':how,'cue_i':cue.i if cue is not None else None}
        elif t.dep_ in {'oc','mo','re','cc','cj'}:
            review.append({'i':t.i,'text':t.text,'reason':'unclassified_finite_dependency'})
    # Elliptical first conjunct with missing auxiliary: do not count its participle.
    # Transfer a shared explicit introducer to the sole finite coordinated head.
    for t in doc:
        if not finite(t) or t.i in out or t.dep_!='cj':continue
        h=t.head
        if h.dep_=='cd':h=h.head
        if not verbish(h) or finite_head_candidate(h)[0]:continue
        cue=next((c for c in h.children if c.dep_=='cp' and c.lower_ in INTRO),None)
        if cue is not None:
            out[t.i]={'i':t.i,'text':t.text,'kind':'I','rule':'shared_introducer_after_auxiliary_ellipsis','finite_evidence':'finite_feature_or_tag','cue_i':cue.i}
    # Optional coordinated-predicate count, deliberately not part of the primary SI.
    coord={}
    for t in doc:
        if not finite(t) or t.i in out:continue
        cur=t
        for _ in range(4):
            if cur.head==cur:break
            if cur.dep_ not in {'cj','cd'}:break
            cur=cur.head
            if cur.i in out:
                coord[t.i]={'i':t.i,'text':t.text,'kind':'C','rule':'coordination_under_marked_head','ancestor':cur.i};break
    return out,coord,review

def depths(sent,heads):
    paths=[]
    for t in sent:
        cur=t.i;seen=[]
        while heads[cur]!=cur:
            if cur in seen:raise ValueError('Dependency cycle')
            seen.append(cur);cur=heads[cur]
            if not sent.start<=cur<sent.end:raise ValueError('Cross-sentence head')
        paths.append((len(seen),t.i,seen+[cur]))
    return max(paths,key=lambda x:x[0])

def source_span(token,mapping):
    m=mapping[token.idx:token.idx+len(token.text)]
    return [min(m),max(m)+1]

def load_old_rule():
    tree=ast.parse((ROOT/'legacy_b3_final.py').read_text())
    ns={'W':{'PWS','PWAV','PWAT'}}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'old_rule','exec'),ns)
    return ns['sub_clause_heads']

def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    src=Path(args.corpus);files=sorted(src.glob('*_cleaned.txt'))
    if len(files)!=9:raise ValueError('Expected exactly nine witnesses')
    overrides=json.loads(Path(args.overrides).read_text()) if args.overrides else []
    clause_fixes=json.loads((ROOT/'reviewed_clause_overrides.json').read_text()) if (ROOT/'reviewed_clause_overrides.json').exists() else []
    clause_used=set()
    used=set();sentences=[];groups=[];changes=[];man=[];old_rule=load_old_rule()
    nlp=spacy.load(args.model);nlp.add_pipe('lu_xun_boundaries',before='parser')
    (out/'corpus').mkdir(exist_ok=True)
    for f in files:
        raw=f.read_text(encoding='utf-8')
        if raw.count('VORWORTENDE')!=1:raise ValueError('Expected one register marker')
        if f.stem=='2019_Pengkun_cleaned':
            assert len(re.findall(r'\bGläubigem\b',raw.split('VORWORTENDE')[1]))==1
        cleaned=[]
        for reg,part in zip(['pref','diary'],raw.split('VORWORTENDE')):
            text,mapping,events=normalize(part,reg,f.stem);cleaned.append(text)
            doc=nlp(text);sents=list(doc.sents)
            for event in events:changes.append(dict(event,witness=f.stem,register=reg))
            pred,coord,review=detect_clauses(doc);old,_=old_rule(doc)
            group=[]
            for si,s in enumerate(sents):
                for ci,fix in enumerate(clause_fixes):
                    if fix['witness']!=f.stem or fix['register']!=reg or fix['sentence_sha256']!=digest(s.text):continue
                    t=s[fix['token_id']-1]
                    assert t.text==fix['text']
                    pred[t.i]={'i':t.i,'text':t.text,'kind':'I','rule':'reviewed_clause_correction','finite_evidence':fix['reason'],'cue_i':s.start+fix['cue_token_id']-1}
                    coord.pop(t.i,None);clause_used.add(ci)
                original={t.i:t.head.i for t in s};heads=original.copy();deps={t.i:t.dep_ for t in s};applied=[]
                for oi,o in enumerate(overrides):
                    if o['witness']!=f.stem or o['register']!=reg or o['sentence_sha256']!=digest(s.text):continue
                    for e in o['edits']:
                        ti=s.start+e['token'];hi=s.start+e['head']
                        assert digest(doc[ti].text)==e['text_sha256'] and digest(doc[hi].text)==e['head_text_sha256']
                        assert original[ti]-s.start==e['expected_old_head']
                        heads[ti]=hi
                        if 'dep' in e:deps[ti]=e['dep']
                    used.add(oi);applied.append(o['reason'])
                orig=depths(s,original);fixed=depths(s,heads)
                rr={'id':f'{f.stem}:{reg}:{si+1:03}','witness':f.stem,'register':reg,'sid':si+1,'text':s.text,'sha256':digest(s.text),
                    'source_span':[mapping[s.start_char],mapping[s.end_char-1]+1],'tokens':[{'id':t.i-s.start+1,'text':t.text,'lemma':t.lemma_,'pos':t.pos_,'tag':t.tag_,'morph':str(t.morph),'head':0 if heads[t.i]==t.i else heads[t.i]-s.start+1,'original_head':0 if original[t.i]==t.i else original[t.i]-s.start+1,'dep':deps[t.i],'original_dep':t.dep_,'source_span':source_span(t,mapping)} for t in s],
                    'clauses':[dict(v,token_id=i-s.start+1,source_span=source_span(doc[i],mapping)) for i,v in pred.items() if s.start<=i<s.end],
                    'coordinated':[dict(v,token_id=i-s.start+1,source_span=source_span(doc[i],mapping)) for i,v in coord.items() if s.start<=i<s.end],
                    'old_rule_count':len([i for i in old if s.start<=i<s.end]),'depth_parser':orig[0],'depth_reviewed':fixed[0],
                    'max_path':[i-s.start+1 for i in fixed[2]],'overrides':applied,
                    'review_flags':[dict(v,token_id=v['i']-s.start+1) for v in review if s.start<=v['i']<s.end]}
                sentences.append(rr);group.append(rr)
            n=len(group);c=sum(len(r['clauses']) for r in group)
            groups.append({'witness':f.stem,'register':reg,'sentences':n,'clauses':c,'index':c/n,'index_with_coord':(c+sum(len(r['coordinated']) for r in group))/n,
                'old_rule_on_cleaned':sum(r['old_rule_count'] for r in group)/n,'depth_parser':statistics.mean(r['depth_parser'] for r in group),'depth_reviewed':statistics.mean(r['depth_reviewed'] for r in group),
                'tokens':sum(len(r['tokens']) for r in group),'review_flags':sum(len(r['review_flags']) for r in group)})
        clean='\n\nVORWORTENDE\n\n'.join(cleaned)+'\n';(out/'corpus'/f.name).write_text(clean)
        man.append({'filename':f.name,'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'analysis_sha256':digest(clean)})
        print(f.name,flush=True)
    if clause_used!=set(range(len(clause_fixes))):raise ValueError('Unapplied clause corrections')
    if used!=set(range(len(overrides))):raise ValueError(f'Unapplied overrides: {set(range(len(overrides)))-used}')
    full=[]
    for f in files:
        gg=[g for g in groups if g['witness']==f.stem];n=sum(g['sentences'] for g in gg);tok=sum(g['tokens'] for g in gg)
        full.append({'witness':f.stem,'sentences':n,'clauses':sum(g['clauses'] for g in gg),'index':sum(g['clauses'] for g in gg)/n,
            'index_with_coord':sum(g['index_with_coord']*g['sentences'] for g in gg)/n,
            'old_rule_on_cleaned':sum(g['old_rule_on_cleaned']*g['sentences'] for g in gg)/n,
            'depth_parser':sum(g['depth_parser']*g['sentences'] for g in gg)/n,
            'depth_reviewed':sum(g['depth_reviewed']*g['sentences'] for g in gg)/n,
            'depth_token_weighted_cleaned':sum(g['depth_reviewed']*g['tokens'] for g in gg)/tok})
    for name,data in [('sentences',sentences),('register_results',groups),('full_results',full),('preprocessing_log',changes),('corpus_manifest',man)]:
        (out/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=1))
    (out/'run_metadata.json').write_text(json.dumps({'version':VERSION,'spacy':spacy.__version__,'model':args.model,'model_version':nlp.meta['version'],'pipeline':nlp.pipe_names,'source':str(src),'overrides_applied':len(used),'clause_overrides_applied':len(clause_used),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--corpus',required=True);ap.add_argument('--output',required=True);ap.add_argument('--model',default='de_core_news_lg');ap.add_argument('--overrides');run(ap.parse_args())
