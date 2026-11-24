"""Verify preserved migration files and explicitly recorded user deletions."""
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


def retired_files():
    """Read exact file records, never skip a whole directory by prefix."""
    path = ROOT / 'docs/retired-versions-2026-11-11.json'
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text())
    if manifest.get('schema_version') != 1:
        raise SystemExit(f'Unsupported retirement manifest schema: {path}')
    records = {}
    for entry in manifest['files']:
        relative = Path(entry['path'])
        if (relative.is_absolute() or '..' in relative.parts
                or relative.as_posix() != entry['path'] or not relative.parts):
            raise SystemExit(f'Invalid retired file path: {entry["path"]}')
        if entry['path'] in records:
            raise SystemExit(f'Duplicate retired file record: {entry["path"]}')
        records[entry['path']] = entry
    return records


def main():
    checked = 0
    retired_count = 0
    failures = []
    layout = ROOT / 'docs/layout-map.json'
    prefixes = json.loads(layout.read_text())['prefixes'] if layout.is_file() else {}
    retired = retired_files()
    for relative in retired:
        path = ROOT / relative
        if path.exists() or path.is_symlink():
            failures.append(f'{relative} (recorded as retired but still present)')
    for name in ['migration-manifest.json', 'reference-copy-manifest.json']:
        manifest = json.loads((ROOT / 'docs' / name).read_text())
        for entry in manifest['files']:
            path = current_path(entry['path'], prefixes)
            retirement = retired.get(path.relative_to(ROOT).as_posix())
            if retirement is not None:
                if (retirement['bytes'] != entry['bytes']
                        or retirement['sha256'] != entry['sha256']):
                    failures.append(f'{entry["path"]} (retirement record differs from original migration)')
                elif not path.exists() and not path.is_symlink():
                    retired_count += 1
                continue
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
    print(f'PASS: {checked} preserved files match migration SHA-256 records; '
          f'{retired_count} migration files are absent as explicitly recorded '
          'in the user-authorized retirement manifest.')


if __name__ == '__main__':
    main()
