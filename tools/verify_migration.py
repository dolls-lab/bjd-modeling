"""Verify preserved migration files without opening or modifying any model."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def current_path(recorded_path, prefixes):
    """Keep historical manifests unchanged while resolving relocated assets."""
    for old, new in sorted(prefixes.items(), key=lambda item: len(item[0]), reverse=True):
        if recorded_path.startswith(old):
            return ROOT / (new + recorded_path[len(old):])
    return ROOT / recorded_path


def sha256(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    checked = 0
    failures = []
    layout = ROOT / 'docs/layout-map.json'
    prefixes = json.loads(layout.read_text())['prefixes'] if layout.is_file() else {}
    for name in ['migration-manifest.json', 'reference-copy-manifest.json']:
        manifest = json.loads((ROOT / 'docs' / name).read_text())
        for entry in manifest['files']:
            path = current_path(entry['path'], prefixes)
            # Caches and duplicate packages were moved but are intentionally
            # untracked. A future checkout does not need these optional files.
            optional = ('__pycache__' in path.parts or path.name == '.DS_Store'
                        or path.suffix in {'.zip', '.pyc', '.pyo'}
                        or path.name.endswith(('.blend1', '.blend2')))
            if not path.is_file() and optional:
                continue
            if not path.is_file() or path.stat().st_size != entry['bytes']:
                failures.append(entry['path'])
            elif sha256(path) != entry['sha256']:
                failures.append(entry['path'])
            checked += 1
    if failures:
        raise SystemExit('Migration mismatches:\n' + '\n'.join(failures))
    print(f'PASS: {checked} preserved files match migration SHA-256 records.')


if __name__ == '__main__':
    main()
