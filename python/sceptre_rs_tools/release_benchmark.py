"""Measure a published release and candidate serially on one host; retain every raw artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import IO, TYPE_CHECKING
from urllib.request import urlopen

if TYPE_CHECKING:
    from collections.abc import Iterable

import tomllib

from sceptre_rs_tools import benchmark as b
from sceptre_rs_tools.publish import published_payload

BASELINE_VERSION = "0.8.1"


def digest(path: Path) -> str:
    """Hash actual artifact bytes rather than a lock-file declaration."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_binary(path: Path, expected: str) -> str:
    """Reject a binary that differs from its independently recorded digest."""
    actual = digest(path)
    if len(expected) != 64 or actual != expected:
        raise ValueError(f"binary SHA256 mismatch: {path}")
    return actual


def _stream_digest(stream: IO[bytes]) -> str:
    hasher = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        hasher.update(chunk)
    return hasher.hexdigest()


def require_distinct(baseline: str, candidate: str) -> None:
    """A candidate cannot provide its own baseline."""
    if baseline == candidate:
        raise ValueError("same binary cannot supply baseline and candidate")


def verify_release_archive(archive: Path, binary: Path) -> dict:
    """Bind baseline executable bytes to the real GitHub release asset digest."""
    release, asset = _published_asset(archive)
    with tarfile.open(archive, "r:gz") as bundle:
        member = _binary_member(bundle)
        stream = bundle.extractfile(member)
        if stream is None or _stream_digest(stream) != digest(binary):
            raise ValueError("baseline executable is not the published archive member")
    with urlopen(
        f"https://api.github.com/repos/xberg-io/sceptre/git/ref/tags/v{BASELINE_VERSION}", timeout=60
    ) as response:
        target = json.load(response)["object"]
    for _ in range(4):
        if target["type"] == "commit":
            break
        if target["type"] != "tag":
            raise ValueError("baseline tag must resolve to a commit")
        with urlopen("https://api.github.com/repos/xberg-io/sceptre/git/tags/" + target["sha"], timeout=60) as response:
            target = json.load(response)["object"]
    if target["type"] != "commit":
        raise ValueError("baseline tag nesting is excessive")
    return {"tag": release["tag_name"], "release_id": release["id"], "asset": asset, "source_revision": target["sha"]}


def _published_asset(archive: Path) -> tuple[dict, dict]:
    url = f"https://api.github.com/repos/xberg-io/sceptre/releases/tags/v{BASELINE_VERSION}"
    with urlopen(url, timeout=60) as response:
        release = json.load(response)
    assets = [asset for asset in release["assets"] if asset["name"] == archive.name]
    if len(assets) != 1 or release.get("draft") or release.get("tag_name") != f"v{BASELINE_VERSION}":
        raise ValueError("baseline release archive not uniquely published")
    asset = assets[0]
    if asset.get("digest") != "sha256:" + digest(archive):
        raise ValueError("baseline release archive SHA256 mismatch")
    if archive.stat().st_size != asset.get("size") or asset["size"] > 256 * 1024 * 1024:
        raise ValueError("baseline release archive size mismatch or oversized")
    return release, asset


def _binary_member(bundle: Iterable[tarfile.TarInfo]) -> tarfile.TarInfo:
    total = 0
    binaries = []
    seen = set()
    for member in bundle:
        if member.name in seen or len(seen) >= 1000:
            raise ValueError("duplicate or excessive baseline archive members")
        seen.add(member.name)
        path = Path(member.name)
        total += member.size
        if path.is_absolute() or ".." in path.parts or member.mode & 0o6000:
            raise ValueError("unsafe baseline archive path or privileged mode")
        if not (member.isfile() or member.isdir()) or total > 256 * 1024 * 1024:
            raise ValueError("unsafe baseline archive link/type or oversized contents")
        if member.isfile() and path.name == "sceptre":
            binaries.append(member)
    if len(binaries) != 1:
        raise ValueError("baseline archive requires exactly one regular binary member")
    return binaries[0]


def prepare_baseline(destination: Path) -> tuple[Path, Path, str]:
    """Download the real published Linux baseline and copy only its verified regular binary."""
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("automatic baseline provisioning requires the Linux x86_64 benchmark job")
    destination.mkdir(parents=True, exist_ok=False)
    name = "sceptre-x86_64-unknown-linux-gnu.tar.gz"
    url = f"https://github.com/xberg-io/sceptre/releases/download/v{BASELINE_VERSION}/{name}"
    archive, binary = destination / name, destination / "sceptre"
    with urlopen(url, timeout=120) as response, archive.open("xb") as output:
        count = 0
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > 256 * 1024 * 1024:
                raise ValueError("baseline archive oversized")
            output.write(chunk)
    _published_asset(archive)
    with tarfile.open(archive, "r:gz") as bundle:
        member = _binary_member(bundle)
        stream = bundle.extractfile(member)
        if stream is None:
            raise ValueError("baseline binary missing")
        binary.write_bytes(stream.read())
    verify_release_archive(archive, binary)
    binary.chmod(0o755)
    return archive, binary, digest(binary)


def _required_equal(left: dict, right: dict, key: str) -> None:
    if not left.get(key) or left.get(key) != right.get(key):
        raise ValueError(f"{key} mismatch or unmeasurable")


def validate_pair(baseline: dict, candidate: dict, images: dict[str, str], before: str, after: str) -> None:
    """Fail closed on incomparable hosts, runtime, config, corpus or missing rows."""
    left, right = baseline["metadata"], candidate["metadata"]
    old_env, new_env = left["environment"], right["environment"]
    if before == after or old_env.get("sceptre_version") != before or new_env.get("sceptre_version") != after:
        raise ValueError("observed binary version does not match independent release identity")
    _validate_environment_and_config(left, right)
    for report in (baseline, candidate):
        _validate_rows(report, images)


def _validate_environment_and_config(left: dict, right: dict) -> None:
    old_env, new_env = left["environment"], right["environment"]
    for key in ("os", "arch", "runner_label", "cpu_count", "platform"):
        if not old_env.get(key) or old_env.get(key) != new_env.get(key):
            raise ValueError(f"host {key} mismatch or unmeasurable")
    for key in ("backend", "accelerator", "onnxruntime", "models", "reference"):
        _required_equal(old_env, new_env, key)
    if not isinstance(old_env["onnxruntime"], dict) or not old_env["onnxruntime"].get("version"):
        raise ValueError("onnxruntime version unmeasurable")
    for key in ("threads", "repeats", "group", "corpus_total"):
        _required_equal(left, right, key)
    if not isinstance(left["threads"], int) or left["threads"] <= 0:
        raise ValueError("threads must be explicit and positive")


def _validate_rows(report: dict, images: dict[str, str]) -> None:
    corpus = report["metadata"]["environment"].get("corpus", {})
    if not corpus.get("resolved") or not images or corpus.get("images") != images:
        raise ValueError("corpus bytes do not match measured input manifest")
    if report["metadata"].get("corpus_total") != len(images):
        raise ValueError("records census differs from expected corpus_total")
    stems = [row["stem"] for row in report["records"]]
    if len(stems) != len(images) or set(stems) != set(images):
        raise ValueError("records missing, duplicate, empty or outside the declared corpus")


def input_manifest(root: Path) -> dict:
    """Hash every selected image and ground truth, rejecting any incomplete corpus."""
    result = {}
    entries = b.build_corpus(root, group="all")
    if not entries or len({entry.stem for entry in entries}) != len(entries):
        raise ValueError("corpus must have a nonzero unique expected row count")
    for entry in entries:
        if entry.image is None or not entry.image.is_file():
            raise ValueError(f"corpus image missing: {entry.stem}")
        if entry.group == "labeled" and (entry.ground_truth is None or not entry.ground_truth.is_file()):
            raise ValueError(f"corpus ground truth missing: {entry.stem}")
        result[entry.stem] = {
            "image_sha256": digest(entry.image),
            "group": entry.group,
            "languages": list(entry.languages),
            "ground_truth_sha256": digest(entry.ground_truth) if entry.ground_truth else None,
        }
    return result


def model_manifest(environment: dict) -> dict:
    """Verify pinned model bytes in the shared Hugging Face cache before and after measurement."""
    home = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface")))
    cache = Path(os.environ.get("HF_HUB_CACHE", str(home / "hub")))
    result = {}
    for model in environment.get("models", []):
        for field in ("repo", "revision", "file", "sha256"):
            if not model.get(field):
                raise ValueError(f"models missing {field}")
        path = cache / ("models--" + model["repo"].replace("/", "--")) / "snapshots" / model["revision"] / model["file"]
        if not path.is_file() or digest(path) != model["sha256"]:
            raise ValueError(f"models bytes missing or SHA256 mismatch: {model.get('name')}")
        result[model["repo"] + "/" + model["file"]] = {"sha256": digest(path), "revision": model["revision"]}
    if not result:
        raise ValueError("models manifest empty")
    return result


def configuration_manifest(root: Path, baseline_revision: str) -> dict[str, str]:
    """Require identical configuration sources to avoid silently comparing changed defaults."""
    paths = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            "HEAD",
            "--",
            "crates/sceptre/src/config",
            "crates/sceptre-cli/src/overrides.rs",
        ],
        cwd=root,
        text=True,
    ).splitlines()
    old_paths = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            baseline_revision,
            "--",
            "crates/sceptre/src/config",
            "crates/sceptre-cli/src/overrides.rs",
        ],
        cwd=root,
        text=True,
    ).splitlines()
    if not paths or paths != old_paths:
        raise ValueError("configuration source manifest empty or file membership changed")
    result = {}
    for path in paths:
        old = subprocess.check_output(["git", "show", baseline_revision + ":" + path], cwd=root)
        current = (root / path).read_bytes()
        if old != current:
            raise ValueError(f"configuration defaults differ from baseline: {path}")
        result[path] = hashlib.sha256(current).hexdigest()
    return result


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _measure(binary: Path, output: Path, threads: int, repeats: int) -> dict:
    command = [
        sys.executable,
        "-m",
        "sceptre_rs_tools.benchmark",
        "--binary",
        str(binary),
        "--group",
        "all",
        "--threads",
        str(threads),
        "--repeats",
        str(repeats),
        "--output-dir",
        str(output),
    ]
    with (output.parent / (output.name + ".log")).open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    return json.loads((output / "comparison.json").read_text())


def _gate(baseline: dict, candidate: dict) -> list[str]:
    records = [b.ImageRecord(**row) for row in candidate["records"]]
    report = b.RunReport(
        metadata=candidate["metadata"],
        records=records,
        aggregates_labeled=candidate["aggregates"]["labeled"],
        aggregates_all=candidate["aggregates"]["all"],
    )
    old_records = [b.ImageRecord(**row) for row in baseline["records"]]
    guardrails = b.derive_guardrails(old_records)
    if not guardrails["contracts"]:
        return ["per-image quality contracts empty"]
    return (
        b.validate_report(report)
        + b.check_thresholds(report, published_payload(baseline))
        + b.check_guardrails(records, guardrails)
    )


def _validate_record_configuration(baseline: dict, candidate: dict, corpus: dict) -> None:
    for report in (baseline, candidate):
        for row in report["records"]:
            expected = corpus[row["stem"]]
            if row["group"] != expected["group"] or row["languages"] != expected["languages"]:
                raise ValueError("per-image configuration identity mismatch")
            if row["group"] != "capability" and row.get("skipped") is not None:
                raise ValueError("expected measured record was skipped")


def _compare(args: argparse.Namespace) -> int:
    """Run two genuine executables serially and retain provenance even when the final gate fails."""
    root = b.repo_root()
    manifest: dict = {"schema_version": 1, "baseline": {}, "candidate": {}}
    for name in ("baseline", "candidate"):
        binary = getattr(args, name + "_binary").resolve()
        manifest[name] = {"binary": str(binary), "sha256": verify_binary(binary, getattr(args, name + "_sha256"))}
    require_distinct(manifest["baseline"]["sha256"], manifest["candidate"]["sha256"])
    manifest["release"] = verify_release_archive(args.baseline_archive, args.baseline_binary)
    manifest["configuration_sources"] = configuration_manifest(root, manifest["release"]["source_revision"])
    manifest["candidate_revision"] = args.candidate_revision
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if current != args.candidate_revision:
        raise ValueError("candidate revision is not the current harness checkout")
    corpus = input_manifest(root)
    languages = sorted({language for entry in b.build_corpus(root, group="all") for language in entry.sceptre_langs})
    old_env = b._sceptre_environment(args.baseline_binary.resolve(), root, languages)
    new_env = b._sceptre_environment(args.candidate_binary.resolve(), root, languages)
    if old_env.get("sceptre_version") != BASELINE_VERSION or new_env.get("sceptre_version") != args.candidate_version:
        raise ValueError("observed binary version differs before measurement")
    if args.candidate_version == BASELINE_VERSION:
        raise ValueError("baseline and candidate version must differ")
    for key in ("backend", "accelerator", "onnxruntime", "models"):
        _required_equal(old_env, new_env, key)
    models = model_manifest(old_env)
    if model_manifest(new_env) != models:
        raise ValueError("models differ before measurement")
    manifest.update(
        {"inputs": corpus, "models": models, "baseline_environment": old_env, "candidate_environment": new_env}
    )
    _write(args.output / "manifest.json", manifest)
    baseline = _measure(args.baseline_binary.resolve(), args.output / "baseline", args.threads, args.repeats)
    _write(args.output / "baseline-published.json", published_payload(baseline))
    candidate = _measure(args.candidate_binary.resolve(), args.output / "candidate", args.threads, args.repeats)
    images = {stem: item["image_sha256"] for stem, item in corpus.items()}
    validate_pair(baseline, candidate, images, BASELINE_VERSION, args.candidate_version)
    _validate_record_configuration(baseline, candidate, corpus)
    if input_manifest(root) != corpus or model_manifest(old_env) != models or model_manifest(new_env) != models:
        raise ValueError("corpus or models changed during measurement")
    for name in ("baseline", "candidate"):
        verify_binary(Path(manifest[name]["binary"]), manifest[name]["sha256"])
    breaches = _gate(baseline, candidate)
    _write(args.output / "gate.json", {"passed": not breaches, "breaches": breaches})
    return int(bool(breaches))


def compare(args: argparse.Namespace) -> int:
    """Preserve failed measurements and their hashes as well as passing evidence."""
    if args.output.exists():
        raise ValueError("output directory already exists; preserve earlier evidence")
    args.output.mkdir(parents=True)
    try:
        if args.baseline_binary is None:
            archive, binary, checksum = prepare_baseline(args.output / "published-release")
            args.baseline_archive, args.baseline_binary, args.baseline_sha256 = archive, binary, checksum
        return _compare(args)
    except Exception as error:
        _write(args.output / "gate.json", {"passed": False, "error": str(error)})
        raise
    finally:
        _write(
            args.output / "artifact-sha256.json",
            {
                str(path.relative_to(args.output)): digest(path)
                for path in sorted(args.output.rglob("*"))
                if path.is_file() and path.name != "artifact-sha256.json"
            },
        )


def main() -> None:
    """Parse the explicit release identities; never infer a baseline from the candidate."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate"):
        parser.add_argument("--" + name + "-binary", type=Path, required=name == "candidate")
        parser.add_argument("--" + name + "-sha256")
    parser.add_argument("--baseline-archive", type=Path)
    parser.add_argument("--candidate-version")
    parser.add_argument("--candidate-revision")
    parser.add_argument("--threads", type=int, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = b.repo_root()
    args.candidate_sha256 = args.candidate_sha256 or digest(args.candidate_binary)
    args.candidate_version = (
        args.candidate_version or tomllib.loads((root / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    )
    args.candidate_revision = (
        args.candidate_revision or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    )
    supplied = [args.baseline_binary, args.baseline_sha256, args.baseline_archive]
    if any(supplied) and not all(supplied):
        parser.error("baseline binary, SHA256 and archive must be supplied together")
    if args.threads <= 0 or args.repeats < 2:
        parser.error("positive explicit threads and at least two repeats are required")
    raise SystemExit(compare(args))


if __name__ == "__main__":
    main()
