"""Check distributed numerical results without accessing translation text."""
from pathlib import Path
import csv
import hashlib
import json
import math
import shlex
import statistics

ROOT = Path(__file__).resolve().parent
S = ROOT / 'analysis/syntax-v3.1.2/results'
A = ROOT / 'analysis/all-analyses-v3.2.1/results'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def close(x, y, tolerance=1e-10):
    if not math.isclose(x, y, rel_tol=0, abs_tol=tolerance):
        raise ValueError(f'Numerical mismatch: {x} versus {y}')


def main():
    sentences = read(S / 'sentence_metrics.json')
    full = read(S / 'full_results.json')
    registers = read(S / 'register_results.json')
    analyses = read(A / 'analyses.json')
    table = read(A / 'table2.json')
    if len(sentences) != 2404 or len(full) != 9 or len(registers) != 18 or len(table) != 9:
        raise ValueError('Unexpected number of observations')
    if len({s['id'] for s in sentences}) != 2404:
        raise ValueError('Duplicate sentence identifiers')
    for group in full + registers:
        rows = [s for s in sentences if s['witness'] == group['witness']
                and ('register' not in group or s['register'] == group['register'])]
        assert len(rows) == group['sentences']
        assert sum(s['clauses'] for s in rows) == group['clauses']
        close(group['index'], group['clauses'] / len(rows))
        close(group['depth_reviewed'], statistics.mean(s['depth_reviewed'] for s in rows))
        close(group['depth_parser'], statistics.mean(s['depth_parser'] for s in rows))
        close(group['index_with_coord'], sum(s['clauses'] + s['coordinated'] for s in rows) / len(rows))
        close(group['old_rule_on_cleaned'], statistics.mean(s['old_rule_count'] for s in rows))
        if 'tokens' in group:
            assert sum(s['tokens'] for s in rows) == group['tokens']
    for track in analyses.values():
        for row in track['rows']:
            assert row['exclusive_count'] == len(row['exclusive_types'])
            for m in row['metrics'].values():
                close(m['words_per_sentence'], m['words'] / m['sentences'])
                close(m['characters_per_word'], m['characters'] / m['words'])
                close(m['syllables_per_word'], m['syllables'] / m['words'])
                close(m['flesch'], 180 - m['words_per_sentence'] - 58.5*m['syllables_per_word'])
                close(m['coleman_liau'], .0588*m['characters']/m['words']*100
                      -.296*m['sentences']/m['words']*100-15.8)
    for row, syn, tab in zip(analyses['corrected']['rows'], full, table):
        assert row['witness'] == syn['witness'] == tab['witness']
        for key, value in row['metrics']['full'].items():
            close(tab[key], value)
        close(tab['subordination_index'], syn['index'])
        close(tab['dependency_depth'], syn['depth_reviewed'])
    delta = read(A/'delta/delta_results.json')
    max_error = 0.0
    count = 0
    for key, track in delta['analyses'].items():
        lines=(A/'delta'/key/'table_with_frequencies.txt').read_text().splitlines()
        values=list(csv.reader(lines,delimiter='\t'))
        if len(values[0])==1:
            values=[shlex.split(line) for line in lines]
        names=values[0]
        frequencies={r[0]:[float(v) for v in r[1:]] for r in values[1:]}
        for level in track['levels'].values():
            positions=[names.index(w) for w in level['witnesses']]
            z=[]
            for feature in level['features']:
                x=[frequencies[feature][i] for i in positions]
                mean=statistics.mean(x); sd=statistics.stdev(x)
                z.append([(v-mean)/sd for v in x])
            for i in range(9):
                for j in range(9):
                    value=statistics.mean(abs(f[i]-f[j]) for f in z)
                    error=abs(value-level['matrix'][i][j])
                    max_error=max(max_error,error)
                    close(value,level['matrix'][i][j],1e-8)
            count+=1
    assert count==25
    control=read(A/'pca_fixed_vocabulary_control.json')
    assert control['fixed_vocabulary_before']==control['fixed_vocabulary_after']
    assert control['fixed_vocabulary_numerically_identical']
    inventory=ROOT/'PUBLIC_FILES.json'
    if inventory.exists():
        for rel, expected in read(inventory)['files'].items():
            file=ROOT/rel
            if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
                raise ValueError(f'Public file has changed: {rel}')
    print(json.dumps({'status':'passed','witnesses':9,'register_groups':18,
                      'sentences':2404,'table2_rows':9,'delta_matrices':count,
                      'delta_max_absolute_error':max_error,
                      'fixed_vocabulary_control_identical':True,
                      'scope':'Numerical consistency; no new linguistic validation.'},indent=2))


if __name__=='__main__':
    main()
