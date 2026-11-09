"""Package only the final post-ear v12 artifacts after internal QA.

This script does not create the QA gate or infer approval from file presence.
After final QA, write final-delivery-ready.json with this minimal schema:

{
  "qa_verified": true,
  "files": {"relative/path.ext": "64-character SHA-256", "...": "..."},
  "checks": [
    {"file": "some-final-report.json", "pointer": "/pass", "equals": true},
    {"file": "some-final-report.json", "pointer": "/inputs/head/sha256",
     "equals_sha256_of": "march7-head-shell-v0.12-draft.stl"}
  ]
}

`files` is the explicit delivery allowlist, including final images, concise
reports, this script, README, parameters, mother data, and both construction
stages' scripts. The checks must also bind both STLs and mother-surface.npz to
their final QA reports using equals_sha256_of. Rendering provenance binds the
final Blend automatically; its listed images must all be in the allowlist.
Report filenames are deliberately not fixed while independent QA is ongoing.

Run --check-only for a read-only preflight. Ordinary execution writes the ZIP
and manifest only after every check succeeds. Never include source PMX,
baseline models, pre-ear copies, rejected candidates, or temporary files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent
GATE_NAME = "final-delivery-ready.json"
BLEND = "march7-bjd-head-v0.12-draft.blend"
HEAD = "march7-head-shell-v0.12-draft.stl"
CAP = "march7-head-cap-v0.12-draft.stl"
MOTHER = "mother-surface.npz"
PROVENANCE = "comparison-renders/v12-render-provenance.json"
ZIP_NAME = "march7-bjd-head-v0.12-draft.zip"
REQUIRED = {
    BLEND, HEAD, CAP, MOTHER, PROVENANCE, "README.md", "package_delivery.py",
    "parameters.json", "source-usage-rules.txt", "actual-eye-geodesic.npz",
    "solve_front.py", "build_head.py", "render_review.py",
}
SUFFIXES = {".blend", ".stl", ".npz", ".py", ".json", ".md", ".txt", ".png"}
EXCLUDED = re.compile(
    r"pre[-_ ]?ear|reject(?:ed)?|baseline|(?:^|[/_. -])(?:tmp|temp|backup)(?:$|[/_. -])",
    re.IGNORECASE,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_path(name: str) -> Path:
    require(isinstance(name, str) and name != "", "Empty or non-string artifact path")
    relative = PurePosixPath(name)
    require(
        not relative.is_absolute() and ".." not in relative.parts
        and "\\" not in name and relative.as_posix() == name,
        f"Unsafe artifact path: {name}",
    )
    path = ROOT / name
    require(path.is_file(), f"Missing artifact: {name}")
    require(path.resolve().is_relative_to(ROOT), f"Artifact escapes delivery directory: {name}")
    require(
        not any((ROOT / PurePosixPath(*relative.parts[:i])).is_symlink()
                for i in range(1, len(relative.parts) + 1)),
        f"Symlink artifact is not allowed: {name}",
    )
    require(path.suffix.lower() in SUFFIXES, f"Unsupported artifact type: {name}")
    require(not EXCLUDED.search(name), f"Non-final or baseline artifact is excluded: {name}")
    require(not any(part.startswith(".") for part in relative.parts), f"Hidden artifact excluded: {name}")
    return path


def json_pointer(document: object, pointer: str) -> object:
    require(isinstance(pointer, str) and pointer.startswith("/"), "Check requires a JSON pointer")
    value = document
    for encoded in pointer[1:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            value = value[int(token)]
        else:
            require(isinstance(value, dict), f"Cannot resolve pointer: {pointer}")
            value = value[token]
    return value


def verify() -> tuple[dict[str, Path], dict[str, dict[str, object]], str]:
    gate_path = ROOT / GATE_NAME
    require(gate_path.is_file(), "Final QA gate is absent; do not package the pre-ear build.")
    gate_hash = sha256(gate_path)
    gate = json.loads(gate_path.read_text())
    require(gate.get("qa_verified") is True, "Final internal QA has not been verified.")
    expected = gate.get("files")
    require(isinstance(expected, dict) and expected, "QA gate must contain an explicit files allowlist.")
    require(GATE_NAME not in expected and "checksums.json" not in expected,
            "The gate and generated manifest must not be self-listed.")
    require(REQUIRED <= expected.keys(), f"Required final artifacts missing: {sorted(REQUIRED - expected.keys())}")

    paths: dict[str, Path] = {}
    manifest: dict[str, dict[str, object]] = {}
    for name, digest in sorted(expected.items()):
        require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                f"Invalid SHA-256 in gate: {name}")
        path = artifact_path(name)
        require(sha256(path) == digest, f"Artifact changed after final QA: {name}")
        paths[name] = path
        manifest[name] = {"sha256": digest, "bytes": path.stat().st_size}
    require("<!-- FINAL_QA_PENDING -->" not in paths["README.md"].read_text(),
            "README is still a preparation draft; finalize its QA status before packaging.")
    require(any("ear" in Path(name).stem.lower() and name.endswith(".py") for name in paths),
            "The actual final ear-refinement script must be included for two-stage reconstruction.")

    checks = gate.get("checks")
    require(isinstance(checks, list) and checks, "Explicit final report checks are required.")
    documents: dict[str, object] = {}
    bound: set[str] = set()
    for check in checks:
        require(isinstance(check, dict), "Each report check must be an object.")
        name = check.get("file")
        require(name in paths and name.endswith(".json"), f"Check report is not hash-pinned: {name}")
        if name not in documents:
            documents[name] = json.loads(paths[name].read_text())
        actual = json_pointer(documents[name], check.get("pointer"))
        require(("equals" in check) != ("equals_sha256_of" in check),
                f"Check must contain exactly one comparison: {name}")
        if "equals_sha256_of" in check:
            target = check["equals_sha256_of"]
            require(target in expected, f"Hash-bound artifact is not pinned: {target}")
            wanted = expected[target]
            bound.add(target)
        else:
            wanted = check["equals"]
        require(type(actual) is type(wanted) and actual == wanted,
                f"Final report check failed: {name} {check.get('pointer')}")
    require({HEAD, CAP, MOTHER} <= bound,
            "Final QA checks must bind both STL hashes and the mother-surface hash.")

    provenance = json.loads(paths[PROVENANCE].read_text())
    require(provenance.get("model_sha256") == expected[BLEND],
            "v12 renders were not made from the final Blend.")
    require(provenance.get("input_model_modified") is False, "Rendering modified its model input.")
    views = provenance.get("views")
    require(isinstance(views, list) and views, "Final rendering provenance has no views.")
    rendered: set[str] = set()
    for view in views:
        filename = view.get("file")
        require(isinstance(filename, str) and filename.startswith("v12-")
                and filename.endswith(".png") and PurePosixPath(filename).name == filename,
                "Unexpected final-render filename.")
        name = "comparison-renders/" + filename
        require(name in paths, f"Final render is not hash-pinned for delivery: {name}")
        rendered.add(filename)
    for suffix in ("front", "quarter", "side", "top", "brow-close", "earback-close", "earback-outside", "crown-close"):
        require(f"v12-{suffix}.png" in rendered, f"Missing final review view: {suffix}")
    require(sha256(gate_path) == gate_hash, "Final QA gate changed during verification.")
    paths[GATE_NAME] = gate_path
    manifest[GATE_NAME] = {"sha256": gate_hash, "bytes": gate_path.stat().st_size}
    return paths, manifest, gate_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Verify final inputs without writing files")
    arguments = parser.parse_args()
    paths, manifest, gate_hash = verify()
    if arguments.check_only:
        print(json.dumps({"verified": True, "written": False, "files": len(paths), "qa_gate_sha256": gate_hash}))
        return

    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    destination = ROOT / ZIP_NAME
    descriptor, temporary_name = tempfile.mkstemp(prefix=".v12-package-", suffix=".tmp", dir=ROOT)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for name, path in sorted(paths.items()):
                bundle.write(path, arcname=name)
            bundle.writestr("checksums.json", manifest_bytes)
        with zipfile.ZipFile(temporary) as bundle:
            require(bundle.testzip() is None, "ZIP integrity check failed.")
            require(set(bundle.namelist()) == set(paths) | {"checksums.json"}, "Unexpected ZIP inventory.")
            for name, record in manifest.items():
                require(hashlib.sha256(bundle.read(name)).hexdigest() == record["sha256"],
                        f"ZIP member differs from verified artifact: {name}")
                require(sha256(paths[name]) == record["sha256"],
                        f"Artifact changed while packaging: {name}")
        os.replace(temporary, destination)
        (ROOT / "checksums.json").write_bytes(manifest_bytes)
    finally:
        temporary.unlink(missing_ok=True)
    print(json.dumps({"zip": str(destination), "bytes": destination.stat().st_size,
                      "sha256": sha256(destination), "files": len(paths), "verified": True,
                      "qa_gate_sha256": gate_hash}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, IndexError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"NOT PACKAGED: {error}") from error
