"""Reproduce analyses in a separate private directory using matching input texts."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
S='analysis/syntax-v3.1.2'
A='analysis/all-analyses-v3.2.1'


def check_corpus(corpus):
    manifest=json.loads((ROOT/S/'results/corpus_manifest.json').read_text())
    actual={p.name:p for p in corpus.glob('*_cleaned.txt')}
    expected={r['filename']:r['source_sha256'] for r in manifest}
    if set(actual)!=set(expected):
        raise ValueError('Input filenames do not match the nine documented witnesses.')
    for name,digest in expected.items():
        content=actual[name].read_bytes()
        if hashlib.sha256(content).hexdigest()!=digest:
            raise ValueError(f'Input hash does not match the archived transcription: {name}')
        if content.decode('utf-8').count('VORWORTENDE')!=1:
            raise ValueError(f'Expected exactly one register separator: {name}')
    return actual


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',required=True,type=Path)
    parser.add_argument('--workdir',type=Path)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    files=check_corpus(args.corpus)
    print('All nine input hashes and register separators match.',flush=True)
    if args.check_only:
        return
    if args.workdir is None:
        parser.error('--workdir is required unless --check-only is used')
    work=args.workdir.resolve()
    if work.exists():
        parser.error('The work directory must not already exist.')
    if work==ROOT or ROOT in work.parents:
        parser.error('Choose a private work directory outside the public repository.')
    for module in ['spacy','numpy','sklearn','de_core_news_lg','de_core_news_md']:
        if importlib.util.find_spec(module) is None:
            parser.error(f'Missing dependency: {module}; see REPRODUCTION.txt')
    rscript=shutil.which('Rscript')
    if rscript is None:
        parser.error('Rscript was not found; see REPRODUCTION.txt')
    # Check R packages before creating the private run.
    subprocess.run([rscript,'-e',"stopifnot(all(vapply(c('stylo','ape','jsonlite'), requireNamespace, logical(1), quietly=TRUE)))"],check=True)
    work.mkdir(parents=True)
    syn=work/S; analysis=work/A
    syn.mkdir(parents=True);analysis.mkdir(parents=True)
    for name in ['pipeline.py','legacy_b3_final.py','reviewed_clause_overrides.json','reviewed_tree_overrides.json']:
        shutil.copyfile(ROOT/S/name,syn/name)
    for name in ['recalculate.py','recalculate_delta.R','check_results.py']:
        shutil.copyfile(ROOT/A/name,analysis/name)
    shutil.copytree(ROOT/A/'inputs',analysis/'inputs')
    original=analysis/'inputs/original_corpus';original.mkdir()
    for name,path in files.items():shutil.copyfile(path,original/name)
    subprocess.run([sys.executable,str(syn/'pipeline.py'),'--corpus',str(original),
                    '--output',str(syn/'results'),'--overrides',str(syn/'reviewed_tree_overrides.json')],check=True)
    shutil.copytree(syn/'results/corpus',analysis/'inputs/corrected_corpus')
    for source,target in [('sentences.json','sentences.json'),('full_results.json','syntax_full.json'),('register_results.json','syntax_register.json')]:
        shutil.copyfile(syn/'results'/source,analysis/'inputs'/target)
    subprocess.run([sys.executable,str(analysis/'recalculate.py')],check=True)
    subprocess.run([rscript,str(analysis/'recalculate_delta.R')],check=True)
    subprocess.run([sys.executable,str(analysis/'check_results.py')],check=True)
    expected=json.loads((ROOT/A/'results/table2.json').read_text())
    observed=json.loads((analysis/'results/table2.json').read_text())
    if observed!=expected:
        raise ValueError('Recalculated Table 2 differs from the distributed values; inspect the private outputs.')
    print('Private recalculation completed. Table 2 matches the distributed values.')
    print('Generated corpus, sentence and concordance files belong only in the private work directory.')


if __name__=='__main__':
    main()
