import sys, json, random
from pathlib import Path
import spacy
nlp = spacy.load("de_core_news_lg")
W = {"PWS","PWAV","PWAT"}
def finite(t): return t.pos_ in ("VERB","AUX") and "Fin" in t.morph.get("VerbForm")
def verb_final(t):
    sub = [d for d in t.subtree if d.i != t.i and d.pos_ not in ("PUNCT",) and d.dep_ not in ("cd","cj")]
    # nur Abhängige im eigenen Satzteil; Konjunkte/Koordination ausgenommen
    return all(d.i < t.i for d in sub if not any(a.dep_ in ("cd","cj") and a.head == t for a in d.ancestors))
def sub_clause_heads(doc):
    heads, kinds = set(), {}
    for t in doc:
        if not finite(t): continue
        cp = [c for c in t.children if c.dep_ == "cp" and c.pos_ == "SCONJ"]
        if cp: heads.add(t.i); kinds[t.i] = "subj"; continue
        if t.dep_ == "rc": heads.add(t.i); kinds[t.i] = "rel"; continue
        if t.dep_ != "ROOT" and any(c.tag_ in W for c in t.children) and verb_final(t):
            heads.add(t.i); kinds[t.i] = "w"
    return heads, kinds
rows, wsamples = [], []
for f in sorted(Path(sys.argv[1]).glob("*_cleaned.txt")):
    text = f.read_text(encoding="utf-8")
    res = {}
    for part, seg in zip(("pref","diary"), [x.strip() for x in text.split("VORWORTENDE",1)]):
        doc = nlp(seg.replace("\n"," "))
        h, k = sub_clause_heads(doc)
        n = len(list(doc.sents))
        res[part] = (len(h), n, sum(1 for v in k.values() if v=="w"))
        wsamples += [(f.stem[:10], doc[i].sent.text[:150], doc[i].text) for i,v in k.items() if v=="w"]
    tot_c = res["pref"][0]+res["diary"][0]; tot_n = res["pref"][1]+res["diary"][1]
    rows.append(dict(witness=f.stem.replace("_cleaned",""), clauses=tot_c, sentences=tot_n,
        index=round(tot_c/tot_n,2), pref=round(res["pref"][0]/res["pref"][1],2),
        diary=round(res["diary"][0]/res["diary"][1],2), w_added=res["pref"][2]+res["diary"][2]))
json.dump(rows, open(Path(sys.argv[1]).parent/"b3_final.json","w"), indent=1)
for r in rows: print(r)
random.seed(3)
print("\nw-Stichprobe (", len(wsamples), "):")
for s in random.sample(wsamples, min(15,len(wsamples))): print(" |", s[2], "::", s[1])
