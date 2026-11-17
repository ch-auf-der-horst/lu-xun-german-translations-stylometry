"""Export only the reviewed public inventory, refusing missing or changed files."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    inventory=json.loads((ROOT/'PUBLIC_FILES.json').read_text())
    paths=[]
    for rel,digest in inventory['files'].items():
        path=ROOT/rel
        if path.is_symlink() or ROOT not in path.resolve().parents:
            raise ValueError(f'Unsafe inventory path: {rel}')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError(f'Public file changed or missing: {rel}')
        paths.append(path)
    paths.extend([ROOT/'PUBLIC_FILES.json',ROOT/'SHA256SUMS'])
    if args.output.exists():
        raise ValueError('Refusing to overwrite an existing archive.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path,ROOT.name+'/'+path.relative_to(ROOT).as_posix())
    print(f'Public archive created: {len(paths)} inventoried files.')


if __name__=='__main__':
    main()
