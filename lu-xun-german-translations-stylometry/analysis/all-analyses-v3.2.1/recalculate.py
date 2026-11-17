#!/usr/bin/env python3
"""Reproduce legacy analyses, isolate five source repairs, and analyse a common corpus.

Run from any directory. All inputs and outputs are relative to this file.
Sentence boundaries and syntax annotations are the recomputed v3.1.2 results.
"""
from pathlib import Path
import json, re, hashlib, platform
from collections import Counter
from difflib import SequenceMatcher
import numpy as np
import sklearn, spacy
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent
IN = ROOT / 'inputs'
OUT = ROOT / 'results'
OUT.mkdir(exist_ok=True)
LABELS = ['Kalmer 1955','Herzfeldt 1958','Beijing 1976','Kraft 1979','Oberbaum 1980',
          'Enlin–Herrmann 1981','Kubin 1994','Pengkun 2019','Kubin 2024']
FIELDS = ['mensch','fressen','essen','menschenfresserei','fleisch','blut','zähne','knochen','verschlingen','kauen']

def read(name): return json.loads((IN/name).read_text(encoding='utf-8'))
def save(name, data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def words(t): return re.findall(r"\b[\wäöüß'-]+\b",t,re.I)
def syllables(w):
    w=w.lower()
    return max(1,len(re.findall('[aeiouäöü]',w))-len(re.findall('ai|au|äu|ei|eu',w)))
def types(t):
    t=re.sub(r'[^\wäöüß\s]',' ',t.lower())
    return set(re.sub(r'\d+',' ',t).split())
def old_sentences(t): return [x for x in re.split(r'(?<=[.!?…])\s+',t) if words(x)]
def profile(t, sentence_texts):
    ws=words(t); n=len(ws); s=len(sentence_texts)
    chars=sum(map(len,ws)); syll=sum(map(syllables,ws))
    return dict(words=n, whitespace_units=len(t.split()),sentences=s,characters=chars,syllables=syll,
                words_per_sentence=n/s,characters_per_word=chars/n,syllables_per_word=syll/n,
                flesch=180-n/s-58.5*syll/n,coleman_liau=.0588*chars/n*100-.296*s/n*100-15.8,
                types=len(types(t)))
def pca(texts,vectorizer):
    x=vectorizer.fit_transform(texts).toarray()
    model=PCA(n_components=2,svd_solver='full')
    xy=model.fit_transform(x)
    # Fix arbitrary component signs for stable comparisons: Kalmer right, Herzfeldt up.
    for j,anchor in [(0,0),(1,1)]:
        if xy[anchor,j]<0: xy[:,j]*=-1
    return dict(features=vectorizer.get_feature_names_out().tolist(),n_features=x.shape[1],
                explained_percent=(model.explained_variance_ratio_*100).tolist(),coordinates=xy.tolist(),
                cosine_similarity=cosine_similarity(x).tolist())

def main():
    paths=sorted((IN/'original_corpus').glob('*_cleaned.txt')); assert len(paths)==9
    names=[p.stem for p in paths]
    original=[p.read_text(encoding='utf-8') for p in paths]
    repaired=list(original)
    for repair in read('text_repairs.json'):
        i=names.index(repair['witness']); assert repaired[i].count(repair['before'])==1
        repaired[i]=repaired[i].replace(repair['before'],repair['after'])
    sentence_rows=read('sentences.json'); assert len(sentence_rows)==2404
    corrected=[]; sentences={}
    for name in names:
        byreg={reg:[s['text'] for s in sentence_rows if s['witness']==name and s['register']==reg] for reg in ['pref','diary']}
        sentences[name]=byreg
        c=(IN/'corrected_corpus'/f'{name}.txt').read_text(encoding='utf-8')
        parts=c.split('VORWORTENDE'); assert len(parts)==2
        for reg,part in zip(['pref','diary'],parts):
            # The lexical and syntactic tracks cover exactly the same characters.
            assert re.sub(r'\s+','',part)==re.sub(r'\s+','',' '.join(byreg[reg])),(name,reg)
        corrected.append(' '.join(' '.join(byreg[r]) for r in ['pref','diary']))
    nlp=spacy.load('de_core_news_md')
    analyses={}
    for track,texts in [('legacy',original),('repairs_only',repaired),('corrected',corrected)]:
        print('Analysing',track,flush=True)
        rows=[]; split_texts={r:[] for r in ['full','pref','diary']}
        sets=[types(t) for t in texts]
        for i,(name,t) in enumerate(zip(names,texts)):
            regtexts={'full':t}
            if track=='corrected': regtexts.update({r:' '.join(sentences[name][r]) for r in ['pref','diary']})
            else: regtexts.update(dict(zip(['pref','diary'],t.split('VORWORTENDE'))))
            metrics={}
            for reg,rt in regtexts.items():
                ss=(sentences[name]['pref']+sentences[name]['diary'] if reg=='full' else sentences[name][reg]) if track=='corrected' else old_sentences(rt)
                metrics[reg]=profile(rt,ss); split_texts[reg].append(rt)
            exclusive=sorted(sets[i]-set().union(*(s for j,s in enumerate(sets) if j!=i)))
            motif={field:sum(field in w.lower() for w in words(t)) for field in FIELDS}
            rows.append(dict(witness=name,label=LABELS[i],metrics=metrics,exclusive_types=exclusive,exclusive_count=len(exclusive),motif=motif))
        lemmas=[' '.join(tok.lemma_.lower() for tok in doc if tok.is_alpha and len(tok.lemma_)>1 and tok.lemma_.lower() not in nlp.Defaults.stop_words) for doc in nlp.pipe([t.lower() for t in texts])]
        analyses[track]=dict(rows=rows,pca_wordform=pca(texts,TfidfVectorizer(max_features=1000)),
            pca_lemma_count=pca(lemmas,CountVectorizer(min_df=2,max_df=.95)),
            pca_lemma_tfidf=pca(lemmas,TfidfVectorizer(min_df=2,max_df=.95)))
        for reg,rt in split_texts.items():
            dest=OUT/'corpora'/track/reg;dest.mkdir(parents=True,exist_ok=True)
            for name,t in zip(names,rt): (dest/f'{name}.txt').write_text(t,encoding='utf-8')
    # Context-reviewed historical categories are fixed annotations, not dictionary reclassification.
    historical=[]
    labels_original=[x.replace('Beijing','Peking') for x in LABELS]
    for i,name in enumerate(names):
        rows=[r for r in read('historical_annotations.json') if r['witness']==labels_original[i] and r['annotation_class'] in ['A','B']]
        counts=Counter()
        for r in rows: counts[r['exact_form']]+=int(r['token_count'])
        diary=' '.join(sentences[name]['diary'])
        source_diary=original[i].split('VORWORTENDE')[1]
        evidence=[]
        for term,n in counts.items():
            pattern=r'(?<!\w)'+re.escape(term).replace(r'\ ',r'\s+')+r'(?!\w)'
            old_hits=list(re.finditer(pattern,source_diary,re.I)); hits=list(re.finditer(pattern,diary,re.I))
            assert len(hits)==len(old_hits),(name,term,len(hits),len(old_hits))
            assert len(hits)>=n,(name,term,len(hits),n)
            # Some modern uses of the same form (e.g. allein) remain excluded by contextual annotation.
            evidence.append(dict(term=term,annotated_tokens=n,all_form_matches=len(hits),
                                 contexts=[diary[max(0,m.start()-100):m.end()+100] for m in hits]))
        n=sum(counts.values()); nw=analyses['corrected']['rows'][i]['metrics']['diary']['words']
        historical.append(dict(witness=name,types=len(counts),tokens=n,diary_words=nw,per_1000=1000*n/nw,evidence=evidence))
    # Recomputed similarity of the two Kubin transcriptions; sequence algorithm is explicit.
    a,b=[words(corrected[i].lower()) for i in [6,8]]
    edition=dict(word_sequence_similarity=SequenceMatcher(None,a,b,autojunk=False).ratio(),
                 wordform_tfidf_cosine=analyses['corrected']['pca_wordform']['cosine_similarity'][6][8])
    # POS counts use the existing corrected syntax annotation; no new parser model is substituted.
    pos=[]
    for name in names:
        for reg in ['full','pref','diary']:
            tokens=[t for s in sentence_rows if s['witness']==name and (reg=='full' or s['register']==reg) for t in s['tokens'] if t['pos'] not in ['SPACE','PUNCT']]
            c=Counter(t['pos'] for t in tokens)
            pos.append(dict(witness=name,register=reg,tokens=len(tokens),counts=dict(c),shares={k:v/len(tokens) for k,v in c.items()}))
    # Compare replicated numerical results with the archived report, at full precision.
    old=read('old_pca_report.json')
    checks={}
    for new,prev in [('pca_wordform','published_fig1'),('pca_lemma_count','methods_lemma_count'),('pca_lemma_tfidf','methods_lemma_tfidf')]:
        observed=np.array(analyses['legacy'][new]['explained_percent'])
        expected=np.array([old[prev][f'pc{i}_variance_ratio']*100 for i in [1,2]])
        checks[new+'_max_percentage_point_difference']=float(np.abs(observed-expected).max())
        assert np.allclose(observed,expected,atol=.00001),(new,observed,expected)
    for row in analyses['corrected']['rows']:
        f=row['metrics']['full'];p=row['metrics']['pref'];d=row['metrics']['diary']
        assert f['words']==p['words']+d['words']
        assert f['sentences']==p['sentences']+d['sentences']
        assert 'vorwortende' not in row['exclusive_types']
    checks['same_sentence_count_as_syntax']=sum(r['metrics']['full']['sentences'] for r in analyses['corrected']['rows'])==2404
    save('analyses.json',analyses);save('historical_markedness.json',historical);save('part_of_speech.json',pos);save('edition_similarity.json',edition);save('checks.json',checks)
    save('manifest.json',dict(version='3.2.1',witness_order=names,labels=LABELS,
         python=platform.python_version(),numpy=np.__version__,scikit_learn=sklearn.__version__,spacy=spacy.__version__,de_core_news_md=nlp.meta['version'],
         input_sha256={str(p.relative_to(IN)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(IN.rglob('*')) if p.is_file()}))
    print(json.dumps(checks,indent=2),flush=True)

if __name__=='__main__': main()
